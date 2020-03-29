#!/usr/bin/python3

from picamera import mmal, mmalobj as mo

camera = mo.MMALCamera()

for o in range(len(camera.outputs)):
 print("Output ",o)
 for a in camera.outputs[o].supported_formats :
  print( hex(a), mmal.FOURCC_str(a) )

resizer=mo.MMALISPResizer()

print( len(resizer.outputs))
for a in resizer.outputs[0].supported_formats :
 print( a, mmal.FOURCC_str(a))
