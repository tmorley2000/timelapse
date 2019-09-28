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
from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops
import distutils.dir_util

parser = argparse.ArgumentParser(description='Timelapse for ZWO ASI cameras', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--zwo-asi-lib', type=str, default=os.getenv('ZWO_ASI_LIB'), help='Location of ASI library, default from ZWO_ASI_LIB')
parser.add_argument('--minexp', type=int, default=0, help='Minimum exposure (us)')
parser.add_argument('--maxexp', type=int, default=10000000, help='Maximum exposure (us)')
parser.add_argument('--mingain', type=float, default=0.0, help='Minimum gain (%% of camera full gain)')
parser.add_argument('--maxgain', type=float, default=98.0, help='Maximum gain (%% of camera full gain)')
parser.add_argument('--idealgain', type=float, default=60.0, help='Ideal gain (%% of camera full gain)')
parser.add_argument('--interval', type=int, default=15, help='Timelapse interval (s)')
parser.add_argument('--dirname', type=str, default="imgs/", help='Directory to save images')
parser.add_argument('--filename', type=str, default="%Y/%m/%d/%Y%m%dT%H%M%S.png", help='Filename template (parsed with strftime, directories automatically created)')
parser.add_argument('--latest', type=str, default="latest.png", help='Name of file to symlink latest image to')
parser.add_argument('--font', type=str, default='/usr/share/fonts/truetype/ttf-bitstream-vera/VeraBd.ttf', help='TTF font file for overlay text')
parser.add_argument('--fontsize', type=int, default=12, help='Font size for overlay text')

args = parser.parse_args()

# Initialize zwoasi with the name of the SDK library
if args.zwo_asi_lib:
    asi.init(args.zwo_asi_lib)
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
controls = camera.get_controls()
for cn in sorted(controls.keys()):
    print('    %s:' % cn)
    for k in sorted(controls[cn].keys()):
        print('        %s: %s' % (k, repr(controls[cn][k])))


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

font=ImageFont.truetype(args.font,args.fontsize)

#Usable Expsure range
minexp=args.minexp
maxexp=args.maxexp

#Usable gain range
mingain=int(float(controls["Gain"]["MaxValue"])*args.mingain/100)
maxgain=int(float(controls["Gain"]["MaxValue"])*args.maxgain/100)

idealgain=float(controls["Gain"]["MaxValue"])*args.idealgain/100

print("Gain: Min %f Max %f Ideal %f"%(mingain,maxgain,idealgain))

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

def saveimage(image,dirname,filename,symlinkname):
	now=time.time()
	image.save(dirname+"/"+filename)
	os.symlink(filename,dirname+"/"+symlinkname+".new")
	os.rename(dirname+"/"+symlinkname+".new",dirname+"/"+symlinkname)
	print "Threaded save to %s in %f"%(filename,time.time()-now)

saverqueue=Queue.Queue()

def saverworker():
	while True:
		(image,dirname,filename,symlinkname)=saverqueue.get()
		saveimage(image,dirname,filename,symlinkname)
		saverqueue.task_done()

worker=threading.Thread(target=saverworker)
worker.setDaemon(True)
worker.start()

# Initial values
#exp0=1
#(gain,exp,exp0)=gainexp(exp0)

# Brightness to target
tgtavg=80

lasttime=time.time()
nexttime=args.interval*int(1+time.time()/args.interval)
frameno=1

#camera.set_image_type(asi.ASI_IMG_RGB24)
camera.set_image_type(asi.ASI_IMG_RAW16)
#camera.set_image_type(asi.ASI_IMG_Y8)

camera.set_control_value(asi.ASI_EXPOSURE,minexp)
camera.set_control_value(asi.ASI_GAIN,mingain)

camera.start_video_capture()

pxls=None

while True:
    now=time.time()
    wait=nexttime-now
#    print "Pause: lasttime %f nexttime %f now %f wait %f"%(lasttime,nexttime,now,wait)
#    while now<nexttime:
#	wait=max(nexttime-now,0.1)
#	time.sleep(wait)
#	lasttime=now
#	now=time.time()
#	print "Sleep:   start %f wait %f late %f"%(lasttime,wait,now-nexttime)
#
#    nexttime+=args.interval

    print "Start:   %f"%(now)

    systemtempfile=open("/sys/class/thermal/thermal_zone0/temp","r")
    systemtemp=float(systemtempfile.readline().strip())/1000
    systemtempfile.close()

    print "Setup:   %f"%(time.time()-now)

#    camera.set_control_value(asi.ASI_GAIN, int(gain))
#    camera.set_control_value(asi.ASI_EXPOSURE, int(exp))

#    print "Capture: %f"%(time.time()-now)

    print "Droppped Frames",camera.get_dropped_frames()
    #pxls=camera.capture()	
    newpxls=camera.capture_video_frame()

    if pxls is None:
	pxls=newpxls.astype("uint32")
    else:
	pxls+=newpxls

    frameno=frameno+1

    if frameno%15!=0:
	continue


    cameratemp=float(camera.get_control_value(asi.ASI_TEMPERATURE)[0])/10

    print "Reshape: %f shape %s type %s"%(time.time()-now,str(pxls.shape),str(pxls.dtype))
    mode = None
    if len(pxls.shape) == 3:
        pxls = pxls[:, :, ::-1]  # Convert BGR to RGB
        mode="RGB"
    if camera.get_image_type() == asi.ASI_IMG_RAW16:
        mode = 'I;16'
        # Simple debayer and convert to 8bit
        r=pxls[::2,::2]
        g1=pxls[1::2,::2]
        g2=pxls[::2,1::2]
        g=((g1+g2)/2)
        b=pxls[1::2,1::2]

        r=numpy.clip(((r.astype(float)/65536)**0.52)*65536,0,65535)
        g=numpy.clip(((g.astype(float)/65536)**0.52)*65536,0,65535)
        b=numpy.clip(((b.astype(float)/65536)**0.52)*65536,0,65535)

        pxls=(numpy.stack((r,g,b),axis=-1)/256).astype("uint8")
        mode="RGB"
    newimage = Image.fromarray(pxls, mode=mode)

    print "Text:    %f"%(time.time()-now)
    width=0
    height=0
    textimage=Image.new(mode,(width,height+1))
    draw=ImageDraw.Draw(textimage)

    text=["%s Exp %d Gain %d"%(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)),int(minexp),int(mingain)),
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

    if "/" in args.filename:
        distutils.dir_util.mkpath(time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(now)))
    filename=time.strftime(args.filename, time.gmtime(now))

    print "Queue Save: %f"%(time.time()-now)
    #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
    saverqueue.put((newimage,args.dirname,filename,args.latest))

    #avg=numpy.average(pxls)
    # Center weight!
#    avg=numpy.average(pxls[(pxls.shape[0]/3):(2*pxls.shape[0]/3),(pxls.shape[1]/3):(2*pxls.shape[1]/3),...])
#    exp0=(exp0*tgtavg/avg+3*exp0)/4
#
#    exp0=max(1.0,exp0)
#
#    (gain,exp,exp0)=gainexp(exp0)
#
#    print("AVG %f EXP0 %f NEWEXP %f NEWGAIN %f" % (avg,exp0,exp,gain))

    pxls=None