#!/usr/bin/python3

from picamera import mmal, mmalobj as mo
import io
import time
from PIL import Image
import numpy
import ctypes as ct
import os

import queue
import threading
import distutils.dir_util

camerainfo=mo.MMALCameraInfo()
camerainfoparams=camerainfo.control.params[mmal.MMAL_PARAMETER_CAMERA_INFO]
camerainfoparamscamera=camerainfoparams.cameras[0]
print("Camera is ",camerainfoparamscamera.camera_name)

(w,h)=(camerainfoparamscamera.max_width,camerainfoparamscamera.max_height)
wsize,hsize=0,0

camera = mo.MMALCamera()

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
                                                                    

t=None
stack=None
stackcount=0
def image_callback(port, buf):
    global t,stack,stackcount,w,h,wsize,hsize
    newt=time.time()
    if t is not None:
        print("interval: %f"%(newt-t))
    t=newt
    
    print("callback %d bytes %d flag"%(len(buf.data),buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END))
    if stack is None:
        stack=numpy.frombuffer(buf.data,numpy.dtype('uint8')).astype('uint32')
        stackcount=1
    else:
        stack+=numpy.frombuffer(buf.data,numpy.dtype('uint8')).astype('uint32')
        stackcount+=1
        if stackcount>=10:
            stack=numpy.clip(stack,0,255)
            stack=stack.reshape([hsize,wsize,3])
            i=Image.fromarray(stack.astype('uint8'),mode="RGB")

            filename=time.strftime("%Y/%m/%d/%Y%m%dT%H%M%S.jpg", time.gmtime(time.time()))
            saverqueue.put((i,"imgs",filename,"latest.jpg"))

            print("N",numpy.min(stack),numpy.max(stack),numpy.average(stack))
            
            
            stack=None
            stackcount=0

    
    #n=numpy.frombuffer(buf.data,numpy.dtype('uint8'))
    #print("N",numpy.min(n),numpy.max(n),numpy.average(n))

    #print(camera.control.params[mmal.MMAL_PARAMETER_ANALOG_GAIN])
    #print(camera.control.params[mmal.MMAL_PARAMETER_DIGITAL_GAIN])
    #print(camera.control.params[mmal.MMAL_PARAMETER_SHUTTER_SPEED])
    cs=camera.control.params[mmal.MMAL_PARAMETER_CAMERA_SETTINGS]
    print(cs.exposure,cs.analog_gain,cs.digital_gain)
    
    return False
    #output.write(buf.data)
    #return bool(buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END)




preview_port=camera.outputs[0]
video_port=camera.outputs[1]
still_port=camera.outputs[2]

camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG]=2

video_port.format = mmal.MMAL_ENCODING_RGB24
video_port.framesize = (w,h)
video_port.commit()
print("video port internal res",video_port._port[0].format[0].es[0].video.width,video_port._port[0].format[0].es[0].video.height)
wsize=video_port._port[0].format[0].es[0].video.width
hsize=video_port._port[0].format[0].es[0].video.height

sc=camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG]
sc.max_stills_w=w
sc.max_stills_h=h
sc.stills_yuv422=0
sc.one_shot_stills=0
sc.max_preview_video_w=w
sc.max_preview_video_h=h
sc.num_preview_video_frames=3
sc.stills_capture_circular_buffer_height=0
sc.fast_preview_resume=0
camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG]=sc
#fps=camera.control.params[mmal.MMAL_PARAMETER_FPS_RANGE]
#fps.fps_low.num=2
#fps.fps_low.den=1
#fps.fps_high.num=2
#fps.fps_high.den=1
fps=mmal.MMAL_PARAMETER_FPS_RANGE_T(
    mmal.MMAL_PARAMETER_HEADER_T(
        mmal.MMAL_PARAMETER_FPS_RANGE,
        ct.sizeof(mmal.MMAL_PARAMETER_FPS_RANGE_T)
    ),
    fps_low=mo.to_rational(2),
    fps_high=mo.to_rational(2),
)

video_port.params[mmal.MMAL_PARAMETER_FPS_RANGE]=fps
em=camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_MODE]
em.value=mmal.MMAL_PARAM_EXPOSUREMODE_NIGHT
camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_MODE]=em
#video_port.params[mmal.MMAL_PARAMETER_MIRROR]=mmal.MMAL_PARAM_MIRROR_BOTH
camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_COMP] = 18
video_port.enable(image_callback)

camera.control.params[mmal.MMAL_PARAMETER_ANALOG_GAIN]=12

print(video_port)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG])
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG])
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].max_stills_w)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].max_stills_h)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].stills_yuv422)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].one_shot_stills)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].max_preview_video_w)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].max_preview_video_h)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].num_preview_video_frames)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].stills_capture_circular_buffer_height)
# print(camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CONFIG].fast_preview_resume)


print(camera.control.params[mmal.MMAL_PARAMETER_EXPOSURE_MODE].value)

camera.outputs[1].params[mmal.MMAL_PARAMETER_CAPTURE] = True
time.sleep(60000)
camera.outputs[1].params[mmal.MMAL_PARAMETER_CAPTURE] = False
camera.outputs[1].disable()
output.close()


# #camera.control.params[mmal.MMAL_PARAMETER_CAMERA_CUSTOM_SENSOR_CONFIG]=2
# camera.outputs[1].format = mmal.MMAL_ENCODING_RGB24
# #camera.outputs[1].format = mmal.MMAL_ENCODING_I420
# print(camera.outputs[1].framesize)
# #camera.outputs[1].framesize = (640, 480)
# camera.outputs[1].framesize = (3280,2464)
# #camera.outputs[1].framesize = (1920,1080)
# camera.outputs[1].commit()
# #camera.outputs[1].buffer_size=100000
# #camera.outputs[1].commit()
# print(camera.outputs[1])
# camera.outputs[1].enable(image_callback)


