#!/usr/bin/python3

from picamera import mmal, mmalobj as mo

camera = mo.MMALCamera()

print("Camera")
for o in range(len(camera.outputs)):
 print("Camera Output ",o)
 for a in camera.outputs[o].supported_formats :
  print( " ",hex(a), mmal.FOURCC_str(a) )

resizer=mo.MMALISPResizer()

print("ISP Resizer") 
for o in range(len(resizer.inputs)):
 print("ISP Resizer Input ",o)
 for a in resizer.inputs[o].supported_formats :
  print( " ",hex(a), mmal.FOURCC_str(a))
for o in range(len(resizer.outputs)):
 print("ISP Resizer Output ",o)
 for a in resizer.outputs[o].supported_formats :
  print( " ",hex(a), mmal.FOURCC_str(a))


encoder=mo.MMALImageEncoder()

print("Image Encoder") 
for o in range(len(encoder.inputs)):
 print("Image Encoder Input ",o)
 for a in encoder.inputs[o].supported_formats :
  print( " ",hex(a), mmal.FOURCC_str(a))
for o in range(len(encoder.outputs)):
 print("Image Encoder Output ",o)
 for a in encoder.outputs[o].supported_formats :
  print( " ",hex(a), mmal.FOURCC_str(a))

print("Camera Info")
mc=mo.MMALCameraInfo()
params=mc.control.params[mmal.MMAL_PARAMETER_CAMERA_INFO]
print("Camera Count",len(params.cameras))
for a in params.cameras:
 if a.max_width>0 and a.max_height>0:
  print(" Camera",a.camera_name)
  print(" width",a.max_width)
  print(" height",a.max_height)
  print(" port",a.port_id)


