#!/usr/bin/env python

#import argparse
import os
import sys
#import time
import zwoasi as asi
import numpy
import math
import Queue
import threading
from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops
import distutils.dir_util
import cv2

##################################################################################
#
# Camera setup
#
def asiinit(zwo_asi_lib,cameraname=None):
    # Initialize zwoasi with the name of the SDK library
    if zwo_asi_lib:
        asi.init(zwo_asi_lib)
    else:
        print('The filename of the SDK library is required set ZWO_ASI_LIB environment variable with the filename')
        sys.exit(1)

    num_cameras = asi.get_num_cameras()
    if num_cameras == 0:
        print('No cameras found')
        sys.exit(0)

    cameras_found = asi.list_cameras()  # Models names of the connected cameras

    if cameraname is not None:
        camera_id=-1
        for n in range(num_cameras):
            if cameraname == cameras_found[n]:
                camera_id=n
                break
        if camera_id==-1:
            print('Unable to find camera "%s".'%(cameraname))
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
    controls = camera.get_controls()
    for cn in sorted(controls.keys()):
        #print('%s: %s' %(cn,map(lambda x: "%s=>%s"%(x,repr(controls[cn][x])), list(controls[cn].keys()))))
        print('%s: %s' %(cn,", ".join(map(lambda x: "%s=>%s"%(x,repr(controls[cn][x])), list(controls[cn].keys())))))


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
    #camera.set_control_value(asi.ASI_AUTO_MAX_BRIGHTNESS, args.tgtbrightness)
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

    return camera,camera_info,controls

##################################################################################
#
# Background thread to save off an image, png or jpeg encoding can be slow!
#
def saveimage(image,dirname,filename,symlinkname):
    if "/" in filename:
        distutils.dir_util.mkpath(os.path.dirname(os.path.join(dirname,filename)))

    image.save(os.path.join(dirname,filename),quality=95)
    os.symlink(filename,os.path.join(dirname,symlinkname+".new"))
    os.rename(os.path.join(dirname,symlinkname+".new"),os.path.join(dirname,symlinkname))
    
saverqueue=Queue.Queue()

def saverworker():
    while True:
	(image,dirname,filename,symlinkname)=saverqueue.get()
	saveimage(image,dirname,filename,symlinkname)
	saverqueue.task_done()
        
saverworkerthread=threading.Thread(target=saverworker)
saverworkerthread.setDaemon(True)
saverworkerthread.start()

##################################################################################
#
# Debayer processing. Either using opencv or just with numpy.
#
# The numpy versions cut the resolution in half, as thats easy!
#
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

    r=r-numpy.min(r)
    g=g-numpy.min(g)
    b=b-numpy.min(b)

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

##################################################################################
#
# System Info
#
def getsystemp():
    systemtempfile=open("/sys/class/thermal/thermal_zone0/temp","r")
    systemtemp=float(systemtempfile.readline().strip())/1000
    systemtempfile.close()

    return systemtemp

##################################################################################
#
# Takes a list of strings and inlays them top left on ofthe image.
#
def inlaytext(img,text,font):
    
    width=0
    height=0
    textimage=Image.new("RGB",(width,height+1))
    draw=ImageDraw.Draw(textimage)

    for line in text:
        (w,h)=draw.textsize(line,font=font)
        if width < (w+2):
            newwidth=w+2
        newheight=height+h
        newtextimage=Image.new("RGB",(newwidth,newheight+1))
        newtextimage.paste(textimage,(0,0))
        draw=ImageDraw.Draw(newtextimage)
        draw.text((1,height),line,font=font)

        width,height,textimage=(newwidth,newheight,newtextimage)

    # Make black box a multiple of 16 on each dimension, useful is pasting into pre-encoded jpg.
    # heightmultiple=16
    # widthmultiple=16

    # newheight=(((height+1-1)/heightmultiple)+1)*heightmultiple
    # newwidth=(((width-1)/widthmultiple)+1)*widthmultiple

    # if width!=newwidth or height!=newheight:
    #     newtextimage=Image.new("RGB",(newwidth,newheight))
    #     newtextimage.paste(textimage,(0,0))
    #     textimage=newtextimage

    img.paste(textimage,(0,0))
    
