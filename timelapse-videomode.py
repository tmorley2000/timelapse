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
import time
import json

swname="timelapse-videomode.py"

import timelapseutils

parser = argparse.ArgumentParser(description='Timelapse for ZWO ASI cameras', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--zwo-asi-lib', type=str, default=os.getenv('ZWO_ASI_LIB'), help='Location of ASI library, default from ZWO_ASI_LIB')
parser.add_argument('--cameraname', type=str, default=None, help='Name of camera to use, if not set will use the first camera found')
parser.add_argument('--exp', type=int, default=15000, help='Maximum exposure and frame duration (ms)')
parser.add_argument('--gain', type=int, default=200, help='Maximum gain (dB*10)')
parser.add_argument('--target', type=int, default=None, help='Target brightness for auto exposure')
parser.add_argument('--gamma', type=int, default=None, help='Camera gamma correction (0-100, 50 default)')
parser.add_argument('--swgamma', type=float, default=1.0, help='Software gamma correction (float, 1.0 default)')
parser.add_argument('--imagemode', default="RGB24", help='Capture mode for the camera', choices=['RGB24','Y8','RAW16','RAW8'])
parser.add_argument('--filename', type=str, default="%Y/%m/%d/%Y%m%dT%H%M%S.jpg", help='Filename template (parsed with strftime, directories automatically created)')
parser.add_argument('--metadata', type=str, default="%Y/%m/%d/metadata.json", help='Separate dump of image metadata')
parser.add_argument('--font', type=str, default='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', help='TTF font file for overlay text')
parser.add_argument('--fontsize', type=int, default=20, help='Font size for overlay text')
parser.add_argument('--linkname', type=str, default="latest.jpg", help='Link to latest image')
parser.add_argument('--dirname', type=str, default="imgs/", help='Directory to save images')
parser.add_argument('--binning', type=int, default=1, help='Image binning')
parser.add_argument('--verbose',  default=False, action='store_true', help='Verbose')

args = parser.parse_args()

camera=timelapseutils.timelapsecamera(args.zwo_asi_lib)
camera.opencamera(args.cameraname,verbose=args.verbose)
camera.set_roi(bins=args.binning)

camera.set_image_type(args.imagemode)

gain=args.gain
gain=max(gain,camera.get_min_gain())
gain=min(gain,camera.get_max_gain())

min_gain=camera.get_min_gain()

exp=args.exp
exp=max(exp,camera.get_min_exposure())
exp=min(exp,camera.get_max_exposure())

print("Set max gain %d, max exp %d"%(gain,exp))
camera.set_gain(min_gain,auto=False)
camera.set_exposure(camera.get_min_exposure(),auto=True)
camera.set_max_auto_gain(gain)
camera.set_max_auto_exposure(exp)

if args.target is not None:
    camera.set_auto_max_brightness(args.target)

camera.set_bandwidth(100)

if args.gamma is not None:
    camera.set_gamma(args.gamma)

camera.set_swgamma(args.swgamma)

camera.start_video_capture()

brightmode=True
delay=0

while True:
    start=time.time()
    dt=datetime.datetime.fromtimestamp(start)

    if args.verbose: print("New frame %s"%(dt.isoformat()))

    pxls=camera.capture_video_frame()

    dt=datetime.datetime.utcnow()

    pxls=camera.postprocessBGR8(pxls)

    metadata=camera.createmetadata(dt,swname=swname)

    if args.verbose: print(" Exp: %f Gain %d"%(metadata["Exposure"],metadata["Gain"]))

    if delay==0:
        if brightmode:
            print("exp=",camera.get_exposure())
            if camera.get_exposure()==exp*1000:
                camera.set_exposure(exp*1000,auto=False)
                camera.set_gain(min_gain,auto=True)
                brightmode=False
                print("switching",brightmode)
                delay=5
        else:
            print("gain=",camera.get_gain())
            if camera.get_gain()==min_gain:
                camera.set_exposure(exp*1000,auto=True)
                camera.set_gain(min_gain,auto=False)
                brightmode=True
                print("switching",brightmode)
                delay=5
    else:
        delay-=1
            

    camera.annotatemetadata(pxls,metadata,font=args.font,fontsize=args.fontsize)

    imagefilename=dt.strftime(args.filename)

    jpeg_bytes=camera.create_jpeg(pxls,camera.create_exif(metadata))

    camera.savejpeg(jpeg_bytes,args.dirname,imagefilename,args.linkname)

    metadatafilename=dt.strftime(args.metadata)

    camera.writemetadata(metadata,imagefilename,args.dirname,metadatafilename)

    time.sleep(max(start+args.exp/1000-time.time(),0))


