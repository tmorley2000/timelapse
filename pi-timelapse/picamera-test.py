#!/usr/bin/python3


import picamera
import itertools
import datetime
from PIL import Image
import numpy
import time

class MyOutput(object):
    def __init__(self):
        self.size = 0
        self.last=datetime.datetime.now()

    def write(self, s):
        self.size += len(s)
        now=datetime.datetime.now()
        print(now-self.last)
        self.last=now
        print('write %d bytes' % len(s))
        global camera
        print(camera.exposure_speed,camera.shutter_speed,camera.resolution)
        print(camera.analog_gain,camera.digital_gain)
        camera.analog_gain=3
        camera.digital_gain=3
        #camera.iso=200
        #i=Image.frombytes("RGB",camera.resolution,s)
        #i.save("imgs/test.jpg")
        #n=numpy.frombuffer(s,numpy.dtype('uint8'))
        #print("N",numpy.min(n),numpy.max(n),numpy.average(n))
        f=open("imgs/test.jpg","wb")
        f.write(s)
        f.close()

    def flush(self):
        print('flush total %d bytes' % self.size)


camera=picamera.PiCamera(resolution="3296x2464",framerate=2,sensor_mode=2)

camera.iso=800
camera.exposure_mode='night'
camera.shutter_speed=500000
print(camera.analog_gain,camera.digital_gain)
#camera.analog_gain=3
#camera.digital_gain=3
#print(camera.analog_gain,camera.digital_gain)

time.sleep(2)


#for a in camera.capture_continuous(MyOutput(),format="bgr",use_video_port=True):
#    pass

camera.capture_sequence(itertools.repeat(MyOutput()),format="jpeg",use_video_port=True)

    



