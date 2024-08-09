#!/usr/bin/env python

import argparse
import os
import sys
import time
import zwoasi as asi
import numpy
import math

import distutils.dir_util



env_filename = os.getenv('ZWO_ASI_LIB')


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
camera_property = camera.get_camera_property()
print('Camera Properties:')
for k in sorted(camera_property.keys()):
    print('    %s: %s' % (k,camera_property[k]))

print ("Camera Supported Modes: %s"%(camera.get_camera_support_mode()))

# Get all of the camera controls
print('')
print('Camera controls:')
controls = camera.get_controls()
for cn in sorted(controls.keys()):
    print('    %s:' % cn)
    for k in sorted(controls[cn].keys()):
        print('        %s: %s' % (k, repr(controls[cn][k])))

sys.exit(0)
