#!/usr/bin/env python

import argparse
import os
import sys
import time
import zwoasi as asi
import numpy
import math

import distutils.dir_util

import timelapseutils

from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops

env_filename = os.getenv('ZWO_ASI_LIB')

fontfile="/usr/share/fonts/truetype/ttf-bitstream-vera/VeraBd.ttf"
fontsize=12
font=ImageFont.truetype(fontfile,fontsize)

camera,camera_info,controls=timelapseutils.asiinit(env_filename)

#Usable Expsure range
minexp=1.0
maxexp=10000000.0

#Usable gain range
#mingain=125
#maxgain=125
mingain=0.0
maxgain=250.0

idealgain=189-30


#def gainexp(targetexp):
#    if targetexp<minexp:
#        return (0,1)
#
#    if targetexp<maxexp:
#        return (0,int(targetexp))
#
#    g=30*math.log(targetexp/maxexp,2)
#
#    if g>maxgain:
#        return(int(maxgain),int(maxexp))
#
#    return (int(g),int(maxexp))

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
	print "gainexp: exp0 %f gain %f exp %f"%(exp0,gain,exp)
	exp0=newexp0
        return (int(gain),int(exp),exp0)


# Initial values
exp0=1
(gain,exp,exp0)=gainexp(exp0)

# Brightness to target
tgtavg=80

# Image every 15 seconds
every=15

lasttime=time.time()
nexttime=every*int(1+time.time()/every)
frameno=1
#filenametemplate="data/img%06d.jpg"
filenametemplate="/img%06d.png"
latest="latest.png"
latestnew="latest.new.png"

camera.set_image_type(asi.ASI_IMG_RGB24)
#camera.set_image_type(asi.ASI_IMG_RAW16)
#camera.set_image_type(asi.ASI_IMG_Y8)

while True:
    now=time.time()
    wait=nexttime-now
    print "Pause: lasttime %f nexttime %f now %f wait %f"%(lasttime,nexttime,now,wait)
    while now<nexttime:
	wait=max(nexttime-now,0.1)
	time.sleep(wait)
	lasttime=now
	now=time.time()
	print "Sleep:   start %f wait %f late %f"%(lasttime,wait,now-nexttime)

    nexttime+=every

    print "Start:   %f"%(now)

    systemtemp=timelapseutils.getsystemp()
    

    print "Setup:   %f"%(time.time()-now)

    camera.set_control_value(asi.ASI_GAIN, int(gain))
    camera.set_control_value(asi.ASI_EXPOSURE, int(exp))

    filename = filenametemplate % frameno
    print "Capture: %f"%(time.time()-now)
    pxls=camera.capture()

    cameratemp=float(camera.get_control_value(asi.ASI_TEMPERATURE)[0])/10

    print "Reshape: %f shape %s type %s"%(time.time()-now,str(pxls.shape),str(pxls.dtype))
    mode = None
    if len(pxls.shape) == 3:
       pxls = pxls[:, :, ::-1]  # Convert BGR to RGB
       mode="RGB"
    if camera.get_image_type() == asi.ASI_IMG_RAW16:
        mode = 'I;16'
    newimage = Image.fromarray(pxls, mode=mode)

    print "Text:    %f"%(time.time()-now)
    width=0
    height=0
    textimage=Image.new("RGB",(width,height+1))
    draw=ImageDraw.Draw(textimage)

    text=["%s Exp %d Gain %d"%(time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)),int(exp),int(gain)),
          "Camera Temp %.1f\260C System Temp %.1f\260C"%(cameratemp,systemtemp),]

    for line in text:
        (w,h)=draw.textsize(line,font=font)
        if width < (w+2):
            newwidth=w+2
        newheight=height+h
        newtextimage=Image.new("RGB",(newwidth,newheight+1))
        newtextimage.paste(textimage,(0,0))

        draw=ImageDraw.Draw(newtextimage)
        draw.text((1,height),line,font=font)

        width=newwidth
        height=newheight
        textimage=newtextimage

    heightmultiple=16
    widthmultiple=16

    newheight=(((height+1-1)/heightmultiple)+1)*heightmultiple
    newwidth=(((width-1)/widthmultiple)+1)*widthmultiple

    if width!=newwidth or height!=newheight:
        newtextimage=Image.new("RGB",(newwidth,newheight))
        newtextimage.paste(textimage,(0,0))
        textimage=newtextimage

    newimage.paste(textimage,(0,0))

    print "Save:    %f"%(time.time()-now)
    dirname="/home/allskycam/zwo-imgs/"
    datedir=time.strftime("%Y/%m/%d/", time.gmtime(now))
    filename=time.strftime("%H%M%S.png", time.gmtime(now))
    distutils.dir_util.mkpath(dirname+datedir)
    newimage.save(dirname+datedir+filename)

    print "Saved:   %f"%(time.time()-now)
    os.symlink(datedir+filename,dirname+"latest.png.new")
    os.rename(dirname+"latest.png.new",dirname+"latest.png")
    #pxls=camera.capture()
    print('Saved to %s' % filename)

    avg=numpy.average(pxls)
    exp0=(exp0*tgtavg/avg+3*exp0)/4

    exp0=max(1.0,exp0)

#    if exp>maxexp:
#        exp=maxexp
#        gain=gain*1.5
#    if exp<minexp:
#        exp=minexp
#        gain=gain*.75
#    if gain>maxgain:
#        gain=maxgain
#    if gain<mingain:
#        gain=mingain

    (gain,exp,exp0)=gainexp(exp0)

    print("AVG %f EXP0 %f NEWEXP %f NEWGAIN %f" % (avg,exp0,exp,gain))
    #save_control_values(filename, camera.get_control_values())


    frameno+=1
    
