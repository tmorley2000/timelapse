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
from string import Template
import datetime

swname="snapshot.py"

import timelapseutils

parser = argparse.ArgumentParser(description='Timelapse for ZWO ASI cameras', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--zwo-asi-lib', type=str, default=os.getenv('ZWO_ASI_LIB'), help='Location of ASI library, default from ZWO_ASI_LIB')
parser.add_argument('--cameraname', type=str, default=None, help='Name of camera to use, if not set will use the first camera found')
parser.add_argument('--exp', type=int, default=32, help='Minimum exposure (us)')
parser.add_argument('--gain', type=int, default=0, help='Minimum gain (%% of camera full gain)')
parser.add_argument('--gamma', type=int, default=None, help='Camera gamma correction (0-100, 50 default)')
parser.add_argument('--swgamma', type=float, default=1.0, help='Software gamma correction (float, 1.0 default)')
parser.add_argument('--imagemode', default="RGB24", help='Capture mode for the camera', choices=['RGB24','Y8','RAW16','RAW8'])
parser.add_argument('--filename', type=str, default="output.jpg", help='Filename (use $count for image number)')
parser.add_argument('--dirname', type=str, default="imgs/", help='Directory to save images')
parser.add_argument('--binning', type=int, default=1, help='Image binning')
parser.add_argument('--count', type=int, default=1, help='Image count')

args = parser.parse_args()

camera=timelapseutils.timelapsecamera(args.zwo_asi_lib)
camera.opencamera(args.cameraname)
camera.set_roi(bins=args.binning)
camera.set_image_type(args.imagemode)

gain=args.gain
gain=max(gain,camera.get_min_gain())
gain=min(gain,camera.get_max_gain())

exp=args.exp
exp=max(exp,camera.get_min_exposure())
exp=min(exp,camera.get_max_exposure())

camera.set_gain( int(gain))
camera.set_exposure( int(exp))

print("Set gain %d, exp %d"%(int(gain),int(exp)))

if args.gamma is not None:
    camera.set_gamma(args.gamma)

camera.set_swgamma(args.swgamma)

filenametemplate=Template(args.filename)

for count in range(args.count):
    pxls=camera.capture()
    pxls=camera.postprocessBGR8(pxls)
    dt=datetime.datetime.utcnow()

    metadata=camera.createmetadata(dt,swname=swname)

    camera.annotatemetadata(pxls,metadata)

    jpeg_bytes=camera.create_jpeg(pxls,camera.create_exif(metadata))

    imagefilename=filenametemplate.substitute(count=count)

    camera.savejpeg(jpeg_bytes,args.dirname,imagefilename,None)
