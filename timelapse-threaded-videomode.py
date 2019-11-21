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
import cv2

parser = argparse.ArgumentParser(description='Timelapse for ZWO ASI cameras', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--zwo-asi-lib', type=str, default=os.getenv('ZWO_ASI_LIB'), help='Location of ASI library, default from ZWO_ASI_LIB')
parser.add_argument('--cameraname', type=str, default=None, help='Name of camera to use, if not set will use the first camera found')
parser.add_argument('--startexp', type=int, default=1000, help='Minimum exposure (ms)')
parser.add_argument('--maxexp', type=int, default=1000000, help='Maximum exposure (ms)')
parser.add_argument('--mingain', type=float, default=0.0, help='Minimum gain (%% of camera full gain)')
parser.add_argument('--maxgain', type=float, default=98.0, help='Maximum gain (%% of camera full gain)')
parser.add_argument('--idealgain', type=float, default=60.0, help='Ideal gain (%% of camera full gain)')
parser.add_argument('--tgtbrightness', type=int, default=100, help='Target brightness valuefor auto exp (50-160)')
parser.add_argument('--interval', type=int, default=15, help='Timelapse interval (s)')
parser.add_argument('--imagemode', default="RGB24", help='Capture mode for the camera', choices=['RGB24','Y8','RAW16','RAW8'])
parser.add_argument('--stacksize', type=int, default=15, help='When camera auto exp is atax, stack this many frames per output frame')
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

if args.cameraname is not None:
    camera_id=-1
    for n in range(num_cameras):
        if args.cameraname == cameras_found[n]:
            camera_id=n
            break
    if camera_id==-1:
        print('Unable to find camera "%s".'%(args.cameraname))
        sys.exit(1)
else:
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

camera.set_control_value(asi.ASI_WB_B, 95)
camera.set_control_value(asi.ASI_WB_R, 52)
camera.set_control_value(asi.ASI_GAMMA, 50)
camera.set_control_value(asi.ASI_BRIGHTNESS, 50)
camera.set_control_value(asi.ASI_AUTO_MAX_BRIGHTNESS, args.tgtbrightness)
camera.set_control_value(asi.ASI_FLIP, 0)

#Reset Camera
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
startexp=args.startexp
maxexp=args.maxexp # Auto exp uses ms not us

#Usable gain range
mingain=float(controls["Gain"]["MaxValue"])*args.mingain/100
maxgain=float(controls["Gain"]["MaxValue"])*args.maxgain/100

idealgain=float(controls["Gain"]["MaxValue"])*args.idealgain/100

print("Gain: Min %f Max %f Ideal %f"%(mingain,maxgain,idealgain))

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

# Brightness to target
tgtavg=80

lasttime=time.time()
nexttime=args.interval*int(1+time.time()/args.interval)
frameno=1

def cvdebayer16to8(pxls):
    #return (cv2.cvtColor(pxls, cv2.COLOR_BAYER_BG2RGB)/256).astype("uint8")
    return cv2.cvtColor((pxls/256).astype("uint8"), cv2.COLOR_BAYER_BG2RGB)

def cvdebayer(pxls):
    return cv2.cvtColor(pxls, cv2.COLOR_BAYER_BG2RGB)


def debayer16to8(pxls):
    r=pxls[::2,::2]
    g1=pxls[1::2,::2].astype("uint32")
    g2=pxls[::2,1::2].astype("uint32")
    g=((g1+g2)/2).astype("uint16")
    b=pxls[1::2,1::2]

#    r=(((r.astype(float)/65536)**0.52)*65536)
#    g=(((g.astype(float)/65536)**0.52)*65536)
#    b=(((b.astype(float)/65536)**0.52)*65536)

    return (numpy.stack((r,g,b),axis=-1)/256).astype("uint8")


def debayer8(pxls):
    r=pxls[::2,::2]
    g1=pxls[1::2,::2].astype("uint16")
    g2=pxls[::2,1::2].astype("uint16")
    g=((g1+g2)/2).astype("uint8")
    b=pxls[1::2,1::2]

#    r=(((r.astype(float)/65536)**0.52)*65536)
#    g=(((g.astype(float)/65536)**0.52)*65536)
#    b=(((b.astype(float)/65536)**0.52)*65536)

    return numpy.stack((r,g,b),axis=-1)


def bgr2rgb(pxls):
    return pxls[:, :, ::-1]  # Convert BGR to RGB

if args.imagemode == "RAW16":
    camera.set_image_type(asi.ASI_IMG_RAW16)
    outputmode='RGB'
    stacktype='uint32'
    clipmin,clipmax=(0,65535)
    postprocess= debayer16to8
    postprocess= cvdebayer16to8
elif args.imagemode == "RAW8":
    camera.set_image_type(asi.ASI_IMG_RAW8)
    outputmode='RGB'
    stacktype='uint16'
    clipmin,clipmax=(0,255)
    postprocess= debayer8
    postprocess= cvdebayer
elif args.imagemode == "Y8":
    camera.set_image_type(asi.ASI_IMG_Y8)
    outputmode='L'
    stacktype='uint16'
    clipmin,clipmax=(0,255)
    postprocess=None
else:
    camera.set_image_type(asi.ASI_IMG_RGB24)
    outputmode='RGB'
    stacktype='uint16'
    clipmin,clipmax=(0,255)
    postprocess=bgr2rgb

#mode = 'I;16' <---- 16 bit raw mode


camera.set_control_value(asi.ASI_GAIN, int(mingain) , True)
camera.set_control_value(asi.ASI_EXPOSURE, startexp*1000, True)

camera.set_control_value(asi.ASI_AUTO_MAX_GAIN, int(maxgain) , True)
camera.set_control_value(asi.ASI_AUTO_MAX_EXP, maxexp , True)

camera.start_video_capture()
dropped=camera.get_dropped_frames()
stacks=[]
while True:
    now=time.time()
    currentexp=camera.get_control_value(asi.ASI_EXPOSURE)[0]/1000
    currentgain=camera.get_control_value(asi.ASI_GAIN)[0]
    currentbrightness=camera.get_control_value(asi.ASI_BRIGHTNESS)[0]
    print "currentexp %d currentgain %d currentbrightness %d"%(currentexp,currentgain,currentbrightness)
    if (currentexp)>=maxexp:
        # Gain at max, stack away
        print "Stacking"
        pxls=camera.capture_video_frame()
	print "Image min: %d avg: %d max: %d"%(numpy.min(pxls),numpy.average(pxls),numpy.max(pxls))
        for a in stacks:
            if a[0]==args.stacksize:
                print "Saving stack of %d frames total exp %d"%(a[0],a[1])
                stacks.remove(a)
                p=a[3]
                # save a
		print "Stack min: %d avg: %d max: %d"%(numpy.min(p),numpy.average(p),numpy.max(p))
		p=numpy.clip(p,clipmin,clipmax)
                if postprocess is not None:
                    p=postprocess(p)
                newimage = Image.fromarray(p, mode=outputmode)
                filename=time.strftime(args.filename, time.gmtime(a[2]))

                if "/" in args.filename:
                    distutils.dir_util.mkpath(args.dirname+"/"+time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(a[2])))

                #print "Queue Save: %f"%(time.time()-now)
                #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
                saverqueue.put((newimage,args.dirname,filename,args.latest))
            else:
                a[0]=a[0]+1
                a[1]=a[1]+currentexp
                a[3]=a[3]+pxls

        if now>=nexttime:
            stacks.append([1,currentexp,now, pxls.astype(stacktype)])
            nexttime+=args.interval
    else:
        # Save and image and pause for a bit.
        print "Not Stacking"
        # Clear out partial stacks
        for a in stacks:
            stacks.remove(a)
            pxls=a[3]
            if postprocess is not None:
                pxls=postprocess(pxls)
            newimage = Image.fromarray(pxls, mode=outputmode)
            filename=time.strftime(args.filename, time.gmtime(a[2]))
            if "/" in args.filename:
                distutils.dir_util.mkpath(args.dirname+"/"+time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(a[2])))

            #print "Queue Save: %f"%(time.time()-now)
            #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
            saverqueue.put((newimage,args.dirname,filename,args.latest))

        wait=nexttime-now
        while now<nexttime:
            wait=max(nexttime-now,0.1)
            time.sleep(wait)
            now=time.time()

        pxls=camera.capture_video_frame()        
	print "Image brightness: %d"%(numpy.average(pxls))
        if postprocess is not None:
            pxls=postprocess(pxls)
        newimage = Image.fromarray(pxls, mode=outputmode)
        filename=time.strftime(args.filename, time.gmtime(now))
        if "/" in args.filename:
            distutils.dir_util.mkpath(args.dirname+"/"+time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(now)))

        #print "Queue Save: %f"%(time.time()-now)
        #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
        saverqueue.put((newimage,args.dirname,filename,args.latest))

        nexttime+=args.interval
            
    
    # now=time.time()
    # wait=nexttime-now
    # print "Pause: lasttime %f nexttime %f now %f wait %f"%(lasttime,nexttime,now,wait)
    # while now<nexttime:
    #     wait=max(nexttime-now,0.1)
    #     time.sleep(wait)
    #     lasttime=now
    #     now=time.time()
    #     print "Sleep:   start %f wait %f late %f"%(lasttime,wait,now-nexttime)

    # nexttime+=args.interval

    # print "Start:   %f"%(now)

    # print "Setup:   %f"%(time.time()-now)

    # print "Capture: %f"%(time.time()-now)
    # pxls=camera.capture_video_frame()

    # cameratemp=float(camera.get_control_value(asi.ASI_TEMPERATURE)[0])/10

    # print "Reshape: %f shape %s type %s"%(time.time()-now,str(pxls.shape),str(pxls.dtype))
    # print "Dropped: %d"%(camera.get_dropped_frames())
    # t0=time.time()
    # if postprocess is not None:
    #     pxls=postprocess(pxls)
    # print "debayer %f"%(time.time()-t0)
    # newimage = Image.fromarray(pxls, mode=outputmode)

    # print "Text:    %f"%(time.time()-now)
    # width=0
    # height=0
    # textimage=Image.new(outputmode,(width,height+1))
    # draw=ImageDraw.Draw(textimage)

    # systemtempfile=open("/sys/class/thermal/thermal_zone0/temp","r")
    # systemtemp=float(systemtempfile.readline().strip())/1000
    # systemtempfile.close()

    # text=["%s Exp %d Gain %d"%(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)),camera.get_control_value(asi.ASI_EXPOSURE)[0],camera.get_control_value(asi.ASI_GAIN)[0]),
    #       "Camera Temp %.1f\260C System Temp %.1f\260C"%(cameratemp,systemtemp),]

    # for line in text:
    #     (w,h)=draw.textsize(line,font=font)
    #     if width < (w+2):
    #         newwidth=w+2
    #     newheight=height+h
    #     newtextimage=Image.new("RGB",(newwidth,newheight+1))
    #     newtextimage.paste(textimage,(0,0))

    #     draw=ImageDraw.Draw(newtextimage)
    #     draw.text((1,height),line,font=font)

    #     width=newwidth
    #     height=newheight
    #     textimage=newtextimage

    # heightmultiple=16
    # widthmultiple=16

    # newheight=(((height+1-1)/heightmultiple)+1)*heightmultiple
    # newwidth=(((width-1)/widthmultiple)+1)*widthmultiple

    # if width!=newwidth or height!=newheight:
    #     newtextimage=Image.new("RGB",(newwidth,newheight))
    #     newtextimage.paste(textimage,(0,0))
    #     textimage=newtextimage

    # newimage.paste(textimage,(0,0))

    # filename=time.strftime(args.filename, time.gmtime(now))

    # if "/" in args.filename:
    #     distutils.dir_util.mkpath(args.dirname+"/"+time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(now)))

    # print "Queue Save: %f"%(time.time()-now)
    # #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
    # saverqueue.put((newimage,args.dirname,filename,args.latest))

    # # #avg=numpy.average(pxls)
    # # # Center weight!
    # # avg=numpy.average(pxls[(pxls.shape[0]/3):(2*pxls.shape[0]/3),(pxls.shape[1]/3):(2*pxls.shape[1]/3),...])
    # # exp0=(exp0*tgtavg/avg+3*exp0)/4

    # # exp0=max(1.0,exp0)

    # # (gain,exp,exp0)=gainexp(exp0)

    # # print("AVG %f EXP0 %f NEWEXP %f NEWGAIN %f" % (avg,exp0,exp,gain))

    # frameno+=1
    
