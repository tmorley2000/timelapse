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
import datetime

swname="timelapse-snapshotmode.py"


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
parser.add_argument('--gamma', type=int, default=None, help='Camera gamma correction (0-100, 50 default)')
parser.add_argument('--swgamma', type=float, default=1.0, help='Software gamma correction (float, 1.0 default)')
parser.add_argument('--imagemode', default="RGB24", help='Capture mode for the camera', choices=['RGB24','Y8','RAW16','RAW8'])
parser.add_argument('--dirname', type=str, default="imgs/", help='Directory to save images')
parser.add_argument('--metadata', type=str, default="%Y/%m/%d/metadata.json", help='Separate dump of image metadata')
parser.add_argument('--filename', type=str, default="%Y/%m/%d/%Y%m%dT%H%M%S.png", help='Filename template (parsed with strftime, directories automatically created)')
parser.add_argument('--linkname', type=str, default="latest.jpg", help='Link to latest image')
parser.add_argument('--latest', type=str, default="latest.png", help='Name of file to symlink latest image to')
parser.add_argument('--binning', type=int, default=1, help='Image binning')
parser.add_argument('--verbose',  default=False, action='store_true', help='Verbose')

args = parser.parse_args()

camera=timelapseutils.timelapsecamera(args.zwo_asi_lib)
camera.opencamera(args.cameraname)
camera.set_roi(bins=args.binning)

if args.gamma is not None:
    camera.set_gamma(args.gamma)

camera.set_swgamma(args.swgamma)

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
tgtavg=128
tgtavg=160

lasttime=time.time()
nexttime=args.interval*int(1+time.time()/args.interval)
frameno=1


camera.set_image_type(args.imagemode)

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
    
    print("Setup:   %f"%(time.time()-now))

    camera.set_gain( int(gain))
    camera.set_exposure( int(exp))

    dt=datetime.datetime.utcnow()

    pxls=camera.capture()
    pxls=camera.postprocessBGR8(pxls)

    cameratemp=camera.get_temperature()
    systemtemp=timelapseutils.getsystemp()

    metadata=camera.createmetadata(dt,swname=swname)
    
    if args.verbose: print(" Exp: %d Gain %d"%(metadata["Exposure"],metadata["Gain"]))

    camera.annotatemetadata(pxls,metadata)

    imagefilename=dt.strftime(args.filename)

    jpeg_bytes=camera.create_jpeg(pxls,camera.create_exif(metadata))

    camera.savejpeg(jpeg_bytes,args.dirname,imagefilename,args.linkname)

    metadatafilename=dt.strftime(args.metadata)

    camera.writemetadata(metadata,imagefilename,args.dirname,metadatafilename)

    avg=numpy.average(pxls[(int(pxls.shape[0]/3)):(2*int(pxls.shape[0]/3)),(int(pxls.shape[1]/3)):(2*int(pxls.shape[1]/3)),...])
    exp0=(exp0*tgtavg/avg+3*exp0)/4

    exp0=max(1.0,exp0)

    (gain,exp,exp0)=gainexp(exp0)

    print(("AVG %f EXP0 %f NEWEXP %f NEWGAIN %f" % (avg,exp0,exp,gain)),flush=True)

    frameno+=1
    
