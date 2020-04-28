#!/usr/bin/env python3

#import argparse
import os
import sys
#import time
import zwoasi as asi
import numpy
import math
import queue
import threading
from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops
import distutils.dir_util
import cv2

##################################################################################
#
# Wrap the ASI camera up in a class
#

class timelapsecamera:
    """Wrapped up camera object"""

    def __init__(self,zwo_asi_lib):
        self.zwo_asi_lib=zwo_asi_lib
        if zwo_asi_lib:
            asi.init(zwo_asi_lib)
        else:
            print('The filename of the SDK library is required set ZWO_ASI_LIB environment variable with the filename')
            sys.exit(1)

    def opencamera(self,cameraname=None):
        num_cameras = asi.get_num_cameras()
        if num_cameras == 0:
            print('No cameras found')
            sys.exit(0)

        cameras_found = asi.list_cameras()  # Models names of the connected cameras

        if cameraname is not None:
            self.camera_id=-1
            for n in range(num_cameras):
                if cameraname == cameras_found[n]:
                    self.camera_id=n
                    break
            if self.camera_id==-1:
                print('Unable to find camera "%s".'%(cameraname))
                sys.exit(1)
        else:
            if num_cameras == 1:
                self.camera_id = 0
                print('Found one camera: %s' % cameras_found[0])
            else:
                print('Found %d cameras' % num_cameras)
                for n in range(num_cameras):
                    print('    %d: %s' % (n, cameras_found[n]))
                    # TO DO: allow user to select a camera
                self.camera_id = 0
        print('Using #%d: %s' % (self.camera_id, cameras_found[self.camera_id]))
        
        self.camera = asi.Camera(self.camera_id)

        # e_per_adu depends on gain, so force it to zero before we start!
        self.camera.set_control_value(asi.ASI_GAIN,0,False)
        self.camera_info = self.camera.get_camera_property()
        self.controls = self.camera.get_controls()



        # Use minimum USB bandwidth permitted
        self.camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, self.camera.get_controls()['BandWidth']['MinValue'])

        # Set some sensible defaults. They will need adjusting depending upon
        # the sensitivity, lens and lighting conditions used.

        self.camera.disable_dark_subtract()

        self.offset_highest_DR,self.offset_unity_gain,self.gain_lowest_RN,self.offset_lowest_RN=asi._get_gain_offset(self.camera_id)

        print("offset_highest_DR %d"%self.offset_highest_DR)
        print("offset_unity_gain %d"%self.offset_unity_gain)
        print("gain_lowest_RN %d"%self.gain_lowest_RN)
        print("offset_lowest_RN %d"%self.offset_lowest_RN)

        print("ElecPerADU %f"%self.camera_info['ElecPerADU'])
        print("BitDepth %d"%self.camera_info['BitDepth'])

        
        unitygain=10*20*math.log10(self.camera_info['ElecPerADU'])
        
        fullwell0=(2**self.camera_info['BitDepth'])*self.camera_info['ElecPerADU']

        print("unitygain %f"%unitygain)
        print("fullwell %f"%fullwell0)

        g=10**(self.gain_lowest_RN/200.0)

        print("g %f"%g)
        print("gfw %f"%(fullwell0/g))

        g=10**(unitygain/200.0)

        print("g %f"%g)
        print("gfw %f"%(fullwell0/g))


        print("Max DR")
        apigain=0
        gain=10**(apigain/200.0)
        fullwell=fullwell0/gain
        print("api-gain %3d gain %2.2f fw %6d"%(apigain,gain,fullwell))
        
        print("Unity Gain")
        apigain=unitygain
        gain=10**(apigain/200.0)
        fullwell=fullwell0/gain
        print("api-gain %3d gain %2.2f fw %6d"%(apigain,gain,fullwell))
        
        print("Lowest RN")
        apigain=self.gain_lowest_RN
        gain=10**(apigain/200.0)
        fullwell=fullwell0/gain
        print("api-gain %3d gain %2.2f fw %6d"%(apigain,gain,fullwell))
        
        self.camera.set_control_value(asi.ASI_WB_B, 95)
        self.camera.set_control_value(asi.ASI_WB_R, 52)
        self.camera.set_control_value(asi.ASI_GAMMA, 50)
        self.camera.set_control_value(asi.ASI_OFFSET, 50)
        self.camera.set_control_value(asi.ASI_FLIP, 0)

        #Reset Camera
        try:
            # Force any single exposure to be halted
            self.camera.stop_video_capture()
            self.camera.stop_exposure()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass


        
    def printcontrols(self):
        for cn in sorted(controls.keys()):
            #print('%s: %s' %(cn,map(lambda x: "%s=>%s"%(x,repr(controls[cn][x])), list(controls[cn].keys()))))
            print('%s: %s' %(cn,", ".join(map(lambda x: "%s=>%s"%(x,repr(controls[cn][x])), list(controls[cn].keys())))))


    def set_auto_max_brightness(self,n):
        self.camera.set_control_value(asi.ASI_AUTO_MAX_BRIGHTNESS, n)

    def get_offset(self):
        return self.camera.get_control_value(asi.ASI_OFFSET)[0]
    def set_offset(self,val,auto=False):
        return self.camera.set_control_value(asi.ASI_OFFSET,val,auto)
        
    def get_max_gain(self):
        return self.controls["Gain"]["MaxValue"]
    def set_max_auto_gain(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_AUTO_MAX_GAIN,val,auto)
        
    def get_gain(self):
        return self.camera.get_control_value(asi.ASI_GAIN)[0]
    def set_gain(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_GAIN,val,auto)

    def get_max_expsure(self):
        return self.controls["Exposure"]["MaxValue"]
    def set_max_auto_exposure(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_AUTO_MAX_EXP,val,auto)
    def get_exposure(self):
        return self.camera.get_control_value(asi.ASI_EXPOSURE)[0]
    def set_exposure(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_EXPOSURE, val, auto)
        
    def get_temperature(self):
        return float(self.camera.get_control_value(asi.ASI_TEMPERATURE)[0])/10
    
    def set_image_type(self,t):
        self.camera.set_image_type(t)


    def start_video_capture(self):
        self.camera.start_video_capture()

    def get_dropped_frames(self):
        return self.camera.get_dropped_frames()

    def capture_video_frame(self):
        return self.camera.capture_video_frame()

    def capture(self):
        return self.camera.capture()
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
    
saverqueue=queue.Queue()

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
    r=(pxls[::2,::2]>>8).astype("uint8")
# Type conversion if camer is true 16bit, for cameras with 15 or less bits, its not necessary
#    g1=pxls[1::2,::2].astype("uint32")
#    g2=pxls[::2,1::2].astype("uint32")
#    g=((g1+g2)/2).astype("uint16")

#    g1=pxls[1::2,::2]
#    g2=pxls[::2,1::2]
#    g=(g1+g2)>>1

    g=((pxls[1::2,::2]+pxls[::2,1::2])>>9).astype("uint8")
    b=(pxls[1::2,1::2]>>8).astype("uint8")

#    r=r-numpy.min(r)
#    g=g-numpy.min(g)
#    b=b-numpy.min(b)

#    r=(((r.astype(float)/65536)**0.52)*65536)
#    g=(((g.astype(float)/65536)**0.52)*65536)
#    b=(((b.astype(float)/65536)**0.52)*65536)

    #return (numpy.stack((r,g,b),axis=-1)/256).astype("uint8")
    #return (numpy.stack((r,g,b),axis=-1)>>8).astype("uint8")
    return numpy.stack((r,g,b),axis=-1)


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
    
