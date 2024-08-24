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
import piexif
import piexif.helper
import json
import io
import simplejpeg
import datetime

##################################################################################
#
# Utility to allow json encoding of datetime
#
class jsondatetimeencoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


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

    def opencamera(self,cameraname=None,verbose=False):
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

        if verbose:
            for a in ['IsColorCam','BayerPattern','SupportedBins','SupportedVideoFormat',]:
                print("%s: %s"%(a,self.camera_info[a]))

        # Use minimum USB bandwidth permitted
        self.camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, self.camera.get_controls()['BandWidth']['MinValue'])

        # Set some sensible defaults. They will need adjusting depending upon
        # the sensitivity, lens and lighting conditions used.

        self.camera.disable_dark_subtract()

        self.offset_highest_DR,self.offset_unity_gain,self.gain_lowest_RN,self.offset_lowest_RN=asi._get_gain_offset(self.camera_id)

        if verbose:
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
        #self.camera.set_control_value(asi.ASI_GAMMA, 50)
        self.camera.set_control_value(asi.ASI_OFFSET, self.offset_unity_gain)
        self.camera.set_control_value(asi.ASI_FLIP, 0)

        self.swgamma=1.0

        #Reset Camera
        try:
            # Force any single exposure to be halted
            self.camera.stop_video_capture()
            self.camera.stop_exposure()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            pass


    def updatecontrols(self):
        self.controls = self.camera.get_controls()
        
    def printcontrols(self):
        for cn in sorted(self.controls.keys()):
            #print('%s: %s' %(cn,map(lambda x: "%s=>%s"%(x,repr(self.controls[cn][x])), list(self.controls[cn].keys()))))
            print('%s: %s' %(cn,", ".join(map(lambda x: "%s=>%s"%(x,repr(self.controls[cn][x])), list(self.controls[cn].keys())))))


    def set_bandwidth(self,b):
        self.camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, b)

    def get_auto_max_brightness(self):
        return self.camera.get_control_value(asi.ASI_AUTO_MAX_BRIGHTNESS)[0]
    def set_auto_max_brightness(self,n):
        self.camera.set_control_value(asi.ASI_AUTO_MAX_BRIGHTNESS, n)

    def get_whitebalance_red(self):
        return self.camera.get_control_value(asi.ASI_WB_B)[0]
    def set_whitebalance_red(self,val):
        self.camera.set_control_value(asi.ASI_WB_B,val)

    def get_whitebalance_blue(self):
        return self.camera.get_control_value(asi.ASI_WB_B)[0]
    def set_whitebalance_blue(self,val):
        self.camera.set_control_value(asi.ASI_WB_B,val)

    def get_offset(self):
        return self.camera.get_control_value(asi.ASI_OFFSET)[0]
    def set_offset(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_OFFSET,val,auto)
        
    def get_gamma(self):
        return self.camera.get_control_value(asi.ASI_GAMMA)[0]
    def set_gamma(self,val):
        self.camera.set_control_value(asi.ASI_GAMMA,val)

    def get_swgamma(self):
        return self.swgamma
    def set_swgamma(self,val):
        self.swgamma=val
        
    def get_min_gain(self):
        return self.controls["Gain"]["MinValue"]
    def get_max_gain(self):
        return self.controls["Gain"]["MaxValue"]

    def set_max_auto_gain(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_AUTO_MAX_GAIN,val,auto)
        
    def get_gain(self):
        return self.camera.get_control_value(asi.ASI_GAIN)[0]
    def set_gain(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_GAIN,val,auto)

    def get_min_exposure(self):
        return self.controls["Exposure"]["MinValue"]
    def get_max_exposure(self):
        return self.controls["Exposure"]["MaxValue"]
    def set_max_auto_exposure(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_AUTO_MAX_EXP,val,auto)
    def get_exposure(self):
        return self.camera.get_control_value(asi.ASI_EXPOSURE)[0]
    def set_exposure(self,val,auto=False):
        self.camera.set_control_value(asi.ASI_EXPOSURE, val, auto)

    def set_roi(self, start_x=None, start_y=None, width=None, height=None, bins=None, image_type=None):
        self.camera.set_roi(start_x,start_y,width,height,bins,image_type);
        
    def get_temperature(self):
        return float(self.camera.get_control_value(asi.ASI_TEMPERATURE)[0])/10
    
    def set_image_type(self,t):
        types={"RAW16":asi.ASI_IMG_RAW16, "RAW8":asi.ASI_IMG_RAW8, "Y8":asi.ASI_IMG_Y8, "RGB24":asi.ASI_IMG_RGB24}
        if t in types:
            t=types[t]

        self.camera.set_image_type(t)

    def get_image_type(self):
        types={asi.ASI_IMG_RAW16:"RAW16", asi.ASI_IMG_RAW8:"RAW8", asi.ASI_IMG_Y8:"Y8", asi.ASI_IMG_RGB24:"RGB24"}

        return types[self.camera.get_image_type()]

    def start_video_capture(self):
        self.camera.start_video_capture()

    def get_dropped_frames(self):
        return self.camera.get_dropped_frames()

    def capture_video_frame(self):
        return self.camera.capture_video_frame()

    def capture(self):
        return self.camera.capture()

    # From https://stackoverflow.com/questions/71734861/opencv-python-lut-for-16bit-image
    def adjust_gamma16(self,image, gamma=1.0):
        if gamma==1.0:
            return image
        # build a lookup table mapping the pixel values [0, 65535] to
        # their adjusted gamma values
        inv_gamma = 1.0 / gamma
        table = ((numpy.arange(0, 65536) / 65535) ** inv_gamma) * 65535

        # Ensure table is 16-bit
        table = table.astype(numpy.uint16)

        # Now just index into this with the intensities to get the output
        return table[image]

    def adjust_gamma(self,image, gamma=1.0):
        if gamma==1.0:
            return image
        # build a lookup table mapping the pixel values [0, 255] to
        # their adjusted gamma values
        inv_gamma = 1.0 / gamma
        table = ((numpy.arange(0, 256) / 255) ** inv_gamma) * 255

        # Ensure table is 16-bit
        table = table.astype(numpy.uint8)

        # Now just index into this with the intensities to get the output
        return table[image]


    def postprocessBGR8(self,pxls):
        t=self.camera.get_image_type()
	
        if t == asi.ASI_IMG_RAW16:
            return cv2.normalize(self.adjust_gamma16(cv2.cvtColor(pxls, cv2.COLOR_BAYER_BG2BGR),self.swgamma),None,0,255,cv2.NORM_MINMAX,dtype=cv2.CV_8U)
            # Convert to 8 bit and then de-bayer, faster? less accurate?
            return self.adjust_gamma(cv2.cvtColor(cv2.normalize(pxls,None,0,255,cv2.NORM_MINMAX,dtype=cv2.CV_8U), cv2.COLOR_BAYER_BG2RGB),self.swgamma)
        elif t == asi.ASI_IMG_RAW8:
            return self.adjust_gamma(cv2.cvtColor(pxls, cv2.COLOR_BAYER_BG2BGR),self.swgamma)
        elif t==asi.ASI_IMG_Y8:
            return self.adjust_gamma(cv2.cvtColor(pxls, cv2.COLOR_BAYER_BG2BGR),self.swgamma)
        else: # Hopefully asi.ASI_IMG_RGB24
            return self.adjust_gamma(pxls,self.swgamma)

    def createmetadata(self,dt,swname="timelapse"):
        return {"Exposure":self.get_exposure()/1000000,
                "Gain":self.get_gain(),
                "Offset":self.get_offset(),
                "AutoExposureTarget":self.get_auto_max_brightness(),
                "WhiteBalanceRed":self.get_whitebalance_red(),
                "WhiteBalanceBlue":self.get_whitebalance_blue(),
                "CameraGamma":self.get_gamma(),
                "SoftwareGamma":self.get_swgamma(),
                "ImageType":self.get_image_type(),
                "Dropped":self.get_dropped_frames(),
                "SystemTemp":"%.1fC"%(getsystemp()),
                "CameraTemp":"%.1fC"%(self.get_temperature()),
                "Software":swname,
                "DateTime":dt
               }

    def annotatemetadata(self,pxls,metadata,font=None,fontsize=None):
        text=[]
        text.append(metadata["DateTime"].isoformat())
        text.append("Exp: %f Gain: %d Offset: %d"%(metadata["Exposure"],metadata["Gain"],metadata["Offset"]))
        text.append("SystemTemp: %s CameraTemp: %s"%(metadata["SystemTemp"],metadata["CameraTemp"]))

        self.annotateimage(pxls,text,font=font,fontsize=fontsize)

    def create_exif(self,metadata):
        zero_ifd = {piexif.ImageIFD.Make: "ZWO",
                    piexif.ImageIFD.Model: self.camera_info['Name'],
                    piexif.ImageIFD.Software: metadata["Software"],
                    piexif.ImageIFD.DateTime: metadata["DateTime"].strftime("%Y:%m:%d %H:%M:%S")}

        exif_ifd = {piexif.ExifIFD.DateTimeOriginal: metadata["DateTime"].strftime("%Y:%m:%d %H:%M:%S"),
                    piexif.ExifIFD.ExposureTime: (int(metadata["Exposure"]*1000000), 1000000),
                    piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(json.dumps(metadata,sort_keys=True,cls=jsondatetimeencoder))}
        exif_bytes = piexif.dump({"0th": zero_ifd, "Exif": exif_ifd})

        return exif_bytes

    def create_jpeg(self,pxls,exif=None):
        jpeg_bytes=simplejpeg.encode_jpeg(pxls, quality=95, colorspace="BGR", colorsubsampling="420")
        if exif is not None:
            new_bytes=io.BytesIO()
            piexif.insert(exif,jpeg_bytes,new_bytes)
            jpeg_bytes=new_bytes.getbuffer()
        return jpeg_bytes

    def savejpeg(self,jpeg_bytes,dirname,filename,linkname=None):
        if '/' in filename:
            os.makedirs(os.path.dirname(os.path.join(dirname,filename)),exist_ok=True)

        with open(os.path.join(dirname,filename),"wb") as file:
            file.write(jpeg_bytes)

        if linkname is not None and linkname != "":
            os.symlink(filename,os.path.join(dirname,linkname+".new"))
            os.rename(os.path.join(dirname,linkname+".new"),os.path.join(dirname,linkname))

    def writemetadata(self,metadata,imagefilename,dirname,filename):
        if filename is not None and filename != "":
            if '/' in filename:
                os.makedirs(os.path.dirname(os.path.join(dirname,filename)),exist_ok=True)
           
            with open(os.path.join(dirname,filename),"a+") as mdfile:
                mdfile.seek(0)
                mdstr=mdfile.read()
                try:
                    mdjson=json.loads(mdstr)
                except json.decoder.JSONDecodeError:
                    print("Invalid or empty metadata json file, resetting")
                    mdjson={}
                mdjson[os.path.basename(imagefilename)]=metadata
                mdfile.seek(0)
                mdfile.truncate()
                mdfile.write(json.dumps(mdjson,sort_keys=True,cls=jsondatetimeencoder))
    
    # Takes a list of strings and inlays them top left on of the image.
    fontcache={}
    def annotateimage(self,pxls,text,foreground=(255,255,255),background=(0,0,0),fontsize=None,origin=(0,30),font=None):
        if fontsize is None:
            fontsize=12
        thickness=-1 # Filled rather than outline
        if isinstance(font,str):
            # Assume its a truetype font name!
            if font not in self.fontcache:
                self.fontcache[font]=cv2.freetype.createFreeType2()
                self.fontcache[font].loadFontData(font,0)
            y=-2
            for line in text:
                (w, h), baseline=self.fontcache[font].getTextSize(line, fontsize, thickness)
                y+=h+6
                cv2.rectangle(pxls,(0,y+1+baseline),(w+2,y-h-2),background,-1)
                self.fontcache[font].putText(pxls, line, (1,y), fontsize, foreground, thickness, cv2.LINE_8, True)
        else:
            if font is None:
                font=cv2.FONT_HERSHEY_SIMPLEX
            # Fudge Factor to make them about the same size as freetype fonts!
            fontsize=fontsize/30
            thickness=2
            y=-2
            for line in text:
                (w, h), baseline=cv2.getTextSize(line,font, fontsize, thickness)
                y+=h+6
                cv2.rectangle(pxls,(0,y+1+baseline),(w+2,y-h-2),background,-1)
                cv2.putText(pxls, line, (1,y), font, fontsize, foreground, thickness)




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
# System Info
#
def getsystemp():
    systemtempfile=open("/sys/class/thermal/thermal_zone0/temp","r")
    systemtemp=float(systemtempfile.readline().strip())/1000
    systemtempfile.close()

    return systemtemp

