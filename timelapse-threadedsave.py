#!/usr/bin/env python3

import argparse
import os
import sys
import time
import zwoasi as asi
import numpy
import math
import queue
import threading
from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops
import distutils.dir_util
import cv2


import timelapseutils

parser = argparse.ArgumentParser(description='Timelapse for ZWO ASI cameras', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--zwo-asi-lib', type=str, default=os.getenv('ZWO_ASI_LIB'), help='Location of ASI library, default from ZWO_ASI_LIB')
parser.add_argument('--cameraname', type=str, default=None, help='Name of camera to use, if not set will use the first camera found')
parser.add_argument('--minexp', type=float, default=32.0, help='Minimum exposure (us)')
parser.add_argument('--maxexp', type=float, default=10000000.0, help='Maximum exposure (us)')
parser.add_argument('--mingain', type=float, default=0.0, help='Minimum gain (%% of camera full gain)')
parser.add_argument('--maxgain', type=float, default=98.0, help='Maximum gain (%% of camera full gain)')
parser.add_argument('--idealgain', type=float, default=60.0, help='Ideal gain (%% of camera full gain)')
parser.add_argument('--interval', type=int, default=15, help='Timelapse interval (s)')
parser.add_argument('--imagemode', default="RGB24", help='Capture mode for the camera', choices=['RGB24','Y8','RAW16','RAW8'])
parser.add_argument('--dirname', type=str, default="imgs/", help='Directory to save images')
parser.add_argument('--filename', type=str, default="%Y/%m/%d/%Y%m%dT%H%M%S.png", help='Filename template (parsed with strftime, directories automatically created)')
parser.add_argument('--latest', type=str, default="latest.png", help='Name of file to symlink latest image to')
parser.add_argument('--font', type=str, default='/usr/share/fonts/truetype/ttf-bitstream-vera/VeraBd.ttf', help='TTF font file for overlay text')
parser.add_argument('--fontsize', type=int, default=12, help='Font size for overlay text')

args = parser.parse_args()

camera=timelapseutils.timelapsecamera(args.zwo_asi_lib)
camera.opencamera(args.cameraname)

font=ImageFont.truetype(args.font,args.fontsize)

#Usable Expsure range
minexp=args.minexp
maxexp=args.maxexp

#Usable gain range
mingain=float(camera.get_max_gain())*args.mingain/100
maxgain=float(camera.get_max_gain())*args.maxgain/100

idealgain=float(camera.get_max_gain())*args.idealgain/100

print(("Gain: Min %f Max %f Ideal %f"%(mingain,maxgain,idealgain)))

# Useful numbers from http://skyinspector.co.uk/zwo-cmos-digital-video-cameras
doublegain=60

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
        print("gainexp: exp0 %f gain %f exp %f"%(exp0,gain,exp))
        exp0=newexp0
        return (int(gain),int(exp),exp0)

# Initial values
exp0=args.minexp*(2**(idealgain/doublegain))
(gain,exp,exp0)=gainexp(exp0)

# Brightness to target
tgtavg=80

lasttime=time.time()
nexttime=args.interval*int(1+time.time()/args.interval)
frameno=1


if args.imagemode == "RAW16":
    camera.set_image_type(asi.ASI_IMG_RAW16)
    outputmode='RGB'
    postprocess= timelapseutils.debayer16to8
    postprocess= timelapseutils.cvdebayer16to8
elif args.imagemode == "RAW8":
    camera.set_image_type(asi.ASI_IMG_RAW8)
    outputmode='RGB'
    postprocess= timelapseutils.debayer8
    postprocess= timelapseutils.cvdebayer
elif args.imagemode == "Y8":
    camera.set_image_type(asi.ASI_IMG_Y8)
    outputmode='L'
    postprocess=None
else:
    camera.set_image_type(asi.ASI_IMG_RGB24)
    outputmode='RGB'
    postprocess=timelapseutils.bgr2rgb

#mode = 'I;16' <---- 16 bit raw mode


while True:
    now=time.time()
    wait=nexttime-now
    print("Pause: lasttime %f nexttime %f now %f wait %f"%(lasttime,nexttime,now,wait))
    while now<nexttime:
        wait=max(nexttime-now,0.1)
        time.sleep(wait)
        lasttime=now
        now=time.time()
        print("Sleep:   start %f wait %f late %f"%(lasttime,wait,now-nexttime))

    nexttime+=args.interval

    print("Start:   %f"%(now))

    systemtemp=timelapseutils.getsystemp()
    
    print("Setup:   %f"%(time.time()-now))

    camera.set_gain( int(gain))
    camera.set_exposure( int(exp))

    print("Capture: %f"%(time.time()-now))
    pxls=camera.capture()

    cameratemp=camera.get_temperature()

    print("Reshape: %f shape %s type %s"%(time.time()-now,str(pxls.shape),str(pxls.dtype)))

    t0=time.time()
    if postprocess is not None:
        pxls=postprocess(pxls)
    print("debayer %f"%(time.time()-t0))
    newimage = Image.fromarray(pxls, mode=outputmode)

    print("Text:    %f"%(time.time()-now))

    text=["%s Exp %d Gain %d"%(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)),int(exp),int(gain)),
          "Camera Temp %.1f\260C System Temp %.1f\260C"%(cameratemp,systemtemp),]

    timelapseutils.inlaytext(newimage,text,font)
    
    filename=time.strftime(args.filename, time.gmtime(now))

    if "/" in args.filename:
        distutils.dir_util.mkpath(args.dirname+"/"+time.strftime(args.filename[:args.filename.rfind("/")],time.gmtime(now)))

    print("Queue Save: %f"%(time.time()-now))
    #saveimage(newimage,args.dirname+"/"+filename,dirname+args.latest)
    timelapseutils.saverqueue.put((newimage,args.dirname,filename,args.latest))

    #avg=numpy.average(pxls)
    # Center weight!
    avg=numpy.average(pxls[(pxls.shape[0]/3):(2*pxls.shape[0]/3),(pxls.shape[1]/3):(2*pxls.shape[1]/3),...])
    exp0=(exp0*tgtavg/avg+3*exp0)/4

    exp0=max(1.0,exp0)

    (gain,exp,exp0)=gainexp(exp0)

    print(("AVG %f EXP0 %f NEWEXP %f NEWGAIN %f" % (avg,exp0,exp,gain)))

    frameno+=1
    
