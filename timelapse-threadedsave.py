#!/usr/bin/env python

import argparse
import os
import sys
import time
import zwoasi as asi
import numpy
import math
import Queue
import threading

import distutils.dir_util


from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops

env_filename = os.getenv('ZWO_ASI_LIB')

fontfile="/usr/share/fonts/truetype/ttf-bitstream-vera/VeraBd.ttf"
fontsize=12
font=ImageFont.truetype(fontfile,fontsize)

# Initialize zwoasi with the name of the SDK library
if env_filename:
    asi.init(env_filename)
else:
    print('The filename of the SDK library is required set ZWO_ASI_LIB environment variable with the filename')
    sys.exit(1)

num_cameras = asi.get_num_cameras()
if num_cameras == 0:
    print('No cameras found')
    sys.exit(0)

cameras_found = asi.list_cameras()  # Models names of the connected cameras

if num_cameras == 1:
    camera_id = 0
    print('Found one camera: %s' % cameras_found[0])
else:
    print('Found %d cameras' % num_cameras)
    for n in range(num_cameras):
        print('    %d: %s' % (n, cameras_found[n]))
    # TO DO: allow user to select a camera
    camera_id = 0
    print('Using #%d: %s' % (camera_id, cameras_found[camera_id]))

camera = asi.Camera(camera_id)
camera_info = camera.get_camera_property()

# Get all of the camera controls
#print('')
#print('Camera controls:')
#controls = camera.get_controls()
#for cn in sorted(controls.keys()):
#    print('    %s:' % cn)
#    for k in sorted(controls[cn].keys()):
#        print('        %s: %s' % (k, repr(controls[cn][k])))


# Use minimum USB bandwidth permitted
camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, camera.get_controls()['BandWidth']['MinValue'])

# Set some sensible defaults. They will need adjusting depending upon
# the sensitivity, lens and lighting conditions used.

camera.disable_dark_subtract()

offset_highest_DR,offset_unity_gain,gain_lowest_RN,offset_lowest_RN=asi._get_gain_offset(camera_id)

#print gain_lowest_RN,offset_lowest_RN

camera.set_control_value(asi.ASI_WB_B, 95)
camera.set_control_value(asi.ASI_WB_R, 52)
camera.set_control_value(asi.ASI_GAMMA, 50)
camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
camera.set_control_value(asi.ASI_FLIP, 0)


#print('Enabling stills mode')
try:
    # Force any single exposure to be halted
    camera.stop_video_capture()
    camera.stop_exposure()
except (KeyboardInterrupt, SystemExit):
    raise
except:
    pass

#Usable Expsure range
minexp=1.0
maxexp=10000000.0

#Usable gain range
#mingain=125
#maxgain=125
mingain=0.0
maxgain=250.0

idealgain=189-30


#def gainexp(targetexp):
#    if targetexp<minexp:
#        return (0,1)
#
#    if targetexp<maxexp:
#        return (0,int(targetexp))
#
#    g=30*math.log(targetexp/maxexp,2)
#
#    if g>maxgain:
#        return(int(maxgain),int(maxexp))
#
#    return (int(g),int(maxexp))

# 30 far too much, even though gain is db*10??
#doublegain=30
doublegain=15

def gainexp(exp0):
        idealexp=exp0/2**(idealgain/doublegain)
        exp=idealexp
        gain=idealgain


        if idealexp < minexp:
         exp=minexp
         gain=doublegain*math.log(exp0/exp,2)
        elif idealexp > maxexp:
         exp=maxexp
         gain=doublegain*math.log(exp0/exp,2)

        if gain<mingain:
         gain=mingain
        elif gain>maxgain:
         gain=maxgain

	newexp0=exp*2**(gain/doublegain)
	print "gainexp: exp0 %f gain %f exp %f"%(exp0,gain,exp)
	exp0=newexp0
        return (int(gain),int(exp),exp0)

def saveimage(image,filename,symlinkname):
	now=time.time()
	image.save(filename)
	os.symlink(filename,symlinkname+".new")
	os.rename(symlinkname+".new",symlinkname)
	print "Threaded save to %s in %f"%(filename,time.time()-now)

saverqueue=Queue.Queue()

def saverworker():
	while True:
		(image,filename,symlinkname)=saverqueue.get()
		saveimage(image,filename,symlinkname)
		saverqueue.task_done()

worker=threading.Thread(target=saverworker)
worker.deamon=True
worker.start()

# Initial values
exp0=1
(gain,exp,exp0)=gainexp(exp0)

# Brightness to target
tgtavg=80

# Image every 15 seconds
every=15

lasttime=time.time()
nexttime=every*int(1+time.time()/every)
frameno=1
#filenametemplate="data/img%06d.jpg"
filenametemplate="/img%06d.png"
latest="latest.png"
latestnew="latest.new.png"

camera.set_image_type(asi.ASI_IMG_RGB24)
#camera.set_image_type(asi.ASI_IMG_RAW16)
#camera.set_image_type(asi.ASI_IMG_Y8)

while True:
    now=time.time()
    wait=nexttime-now
    print "Pause: lasttime %f nexttime %f now %f wait %f"%(lasttime,nexttime,now,wait)
    while now<nexttime:
	wait=max(nexttime-now,0.1)
	time.sleep(wait)
	lasttime=now
	now=time.time()
	print "Sleep:   start %f wait %f late %f"%(lasttime,wait,now-nexttime)

    nexttime+=every

    print "Start:   %f"%(now)

    systemtempfile=open("/sys/class/thermal/thermal_zone0/temp","r")
    systemtemp=float(systemtempfile.readline().strip())/1000
    systemtempfile.close()

    print "Setup:   %f"%(time.time()-now)

    camera.set_control_value(asi.ASI_GAIN, int(gain))
    camera.set_control_value(asi.ASI_EXPOSURE, int(exp))

    filename = filenametemplate % frameno
    print "Capture: %f"%(time.time()-now)
    pxls=camera.capture()

    cameratemp=float(camera.get_control_value(asi.ASI_TEMPERATURE)[0])/10

    print "Reshape: %f shape %s type %s"%(time.time()-now,str(pxls.shape),str(pxls.dtype))
    mode = None
    if len(pxls.shape) == 3:
       pxls = pxls[:, :, ::-1]  # Convert BGR to RGB
       mode="RGB"
    if camera.get_image_type() == asi.ASI_IMG_RAW16:
        mode = 'I;16'
    newimage = Image.fromarray(pxls, mode=mode)

    print "Text:    %f"%(time.time()-now)
    width=0
    height=0
    textimage=Image.new("RGB",(width,height+1))
    draw=ImageDraw.Draw(textimage)

    text=["%s Exp %d Gain %d"%(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)),int(exp),int(gain)),
          "Camera Temp %.1f\260C System Temp %.1f\260C"%(cameratemp,systemtemp),]

    for line in text:
        (w,h)=draw.textsize(line,font=font)
        if width < (w+2):
            newwidth=w+2
        newheight=height+h
        newtextimage=Image.new("RGB",(newwidth,newheight+1))
        newtextimage.paste(textimage,(0,0))

        draw=ImageDraw.Draw(newtextimage)
        draw.text((1,height),line,font=font)

        width=newwidth
        height=newheight
        textimage=newtextimage

    heightmultiple=16
    widthmultiple=16

    newheight=(((height+1-1)/heightmultiple)+1)*heightmultiple
    newwidth=(((width-1)/widthmultiple)+1)*widthmultiple

    if width!=newwidth or height!=newheight:
        newtextimage=Image.new("RGB",(newwidth,newheight))
        newtextimage.paste(textimage,(0,0))
        textimage=newtextimage

    newimage.paste(textimage,(0,0))

    dirname="/home/allskycam/zwo-imgs/"
    datedir=time.strftime("%Y/%m/%d/", time.gmtime(now))
    distutils.dir_util.mkpath(dirname+datedir)
    filename=time.strftime("%Y%m%dT%H%M%S.png", time.gmtime(now))

    print "Queue Save: %f"%(time.time()-now)
    #saveimage(newimage,dirname+datedir+filename,dirname+"latest.png")
    saverqueue.put((newimage,dirname+datedir+filename,dirname+"latest.png"))

    #avg=numpy.average(pxls)
    # Center weight!
    print "%s %s"%(str(pxls.shape),str(pxls[(pxls.shape[0]/3):(2*pxls.shape[0]/3),(pxls.shape[1]/3):(2*pxls.shape[1]/3),...].shape))
    avg=numpy.average(pxls[(pxls.shape[0]/3):(2*pxls.shape[0]/3),(pxls.shape[1]/3):(2*pxls.shape[1]/3),...])
    exp0=(exp0*tgtavg/avg+3*exp0)/4

    exp0=max(1.0,exp0)

#    if exp>maxexp:
#        exp=maxexp
#        gain=gain*1.5
#    if exp<minexp:
#        exp=minexp
#        gain=gain*.75
#    if gain>maxgain:
#        gain=maxgain
#    if gain<mingain:
#        gain=mingain

    (gain,exp,exp0)=gainexp(exp0)

    print("AVG %f EXP0 %f NEWEXP %f NEWGAIN %f" % (avg,exp0,exp,gain))
    #save_control_values(filename, camera.get_control_values())


    frameno+=1
    
