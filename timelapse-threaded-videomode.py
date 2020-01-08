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

import timelapseutils

parser = argparse.ArgumentParser(description='Timelapse for ZWO ASI cameras', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--zwo-asi-lib', type=str, default=os.getenv('ZWO_ASI_LIB'), help='Location of ASI library, default from ZWO_ASI_LIB')
parser.add_argument('--cameraname', type=str, default=None, help='Name of camera to use, if not set will use the first camera found')
parser.add_argument('--startexp', type=int, default=1, help='Minimum exposure (ms)')
parser.add_argument('--maxexp', type=int, default=1000, help='Maximum exposure (ms)')
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

camera=timelapseutils.timelapsecamera(args.zwo_asi_lib)
camera.opencamera(args.cameraname)

# Set target brightness for auto gain
camera.set_auto_max_brightness(args.tgtbrightness)

font=ImageFont.truetype(args.font,args.fontsize)

#Usable Expsure range
startexp=args.startexp
maxexp=args.maxexp # Auto exp uses ms not us

#Usable gain range
mingain=float(camera.get_max_gain())*args.mingain/100
maxgain=float(camera.get_max_gain())*args.maxgain/100

idealgain=float(camera.get_max_gain())*args.idealgain/100

print("Gain: Min %f Max %f Ideal %f"%(mingain,maxgain,idealgain))

lasttime=time.time()
nexttime=args.interval*int(1+time.time()/args.interval)
frameno=1

tgtbrightness=args.tgtbrightness

if args.imagemode == "RAW16":
    camera.set_image_type(asi.ASI_IMG_RAW16)
    outputmode='RGB'
    stacktype='uint32'
    clipmin,clipmax=(0,65535)
    postprocess= timelapseutils.debayer16to8
    postprocess= timelapseutils.cvdebayer16to8
    tgtbrightness=tgtbrightness*256
elif args.imagemode == "RAW8":
    camera.set_image_type(asi.ASI_IMG_RAW8)
    outputmode='RGB'
    stacktype='uint16'
    clipmin,clipmax=(0,255)
    postprocess= timelapseutils.debayer8
    postprocess= timelapseutils.cvdebayer
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
    postprocess=timelapseutils.bgr2rgb

camera.set_gain( int(mingain) , True)
camera.set_exposure( startexp*1000, True)

camera.set_max_auto_gain( int(maxgain) , True)
camera.set_max_auto_exposure( maxexp , True)

camera.start_video_capture()
dropped=camera.get_dropped_frames()
stacks=[]
while True:
    now=time.time()
    pxls=camera.capture_video_frame()
    print "Frame min: %d avg: %d max: %d"%(numpy.min(pxls),numpy.average(pxls),numpy.max(pxls))
    rawexp=camera.get_exposure()
    currentexp=rawexp/1000
    currentgain=camera.get_gain()
    currentbrightness=camera.get_brightness()
    print "currentexp %d currentgain %d currentbrightness %d"%(rawexp,currentgain,currentbrightness)
    if (currentexp)>=maxexp:
        # Gain at max, stack away
        print "Stacking"
        for a in stacks:
            if numpy.average(a[3])>tgtbrightness or a[0]==args.stacksize:
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
                timelapseutils.saverqueue.put((newimage,args.dirname,filename,args.latest))
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
            timelapseutils.saverqueue.put((newimage,args.dirname,filename,args.latest))

        wait=nexttime-now
        while now<nexttime:
            wait=max(nexttime-now,0.1)
            time.sleep(wait)
            now=time.time()

        if postprocess is not None:
            pxls=postprocess(pxls)
        newimage = Image.fromarray(pxls, mode=outputmode)
        filename=time.strftime(args.filename, time.gmtime(now))
        if "/" in args.filename:
            distutils.dir_util.mkpath(args.dirname+"/"+time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(now)))

        #print "Queue Save: %f"%(time.time()-now)
        #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
        timelapseutils.saverqueue.put((newimage,args.dirname,filename,args.latest))

        nexttime+=args.interval
            
    
    
