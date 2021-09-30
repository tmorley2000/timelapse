#!/usr/bin/env python3
# Web streaming example
# Source code from the official PiCamera package
# http://picamera.readthedocs.io/en/latest/recipes2.html#web-streaming

import io
import picamerax as picamera
import logging
import socketserver
from threading import Condition,Thread
from http import server
import time
from datetime import datetime
from urllib.parse import urlparse,parse_qs
from cgi import FieldStorage
import os

PAGE="""\
<html>
<head>
<title>Raspberry Pi - Surveillance Camera</title>
</head>
<body>
<center><h1>Raspberry Pi - Surveillance Camera</h1></center>
<form action="/action" method="post">
<center>
              <button name="id" value="starttimelapse" type="submit">Start Timelapse</button>
              <button name="id" value="startstreaming" type="submit">Start Streaming</button>
              <button name="id" value="startfocusstreaming" type="submit">Start Focus Streaming</button>
              <button name="id" value="stop" type="submit">Stop</button>
</center>
<center>
<table>
<tr><td><button name="id" value="focusTL" type="submit">TL</button></td><td><button name="id" value="focusTC" type="submit">TC</button></td><td><button name="id" value="focusTR" type="submit">TR</button></td></tr>
<tr><td><button name="id" value="focusCL" type="submit">CL</button></td><td><button name="id" value="focusCC" type="submit">CC</button></td><td><button name="id" value="focusCR" type="submit">CR</button></td></tr>
<tr><td><button name="id" value="focusBL" type="submit">BL</button></td><td><button name="id" value="focusBC" type="submit">BC</button></td><td><button name="id" value="focusBR" type="submit">BR</button></td></tr>
</table>
</center>
</form>
<center><img src="stream.mjpg" ></center>
</body>
</html>
"""



class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        #print("frame exp",self.cam.exposure_speed,"len",len(buf))
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class FileOutput(object):
    def __init__(self):
        self.output=None

    def write(self, buf):
        print("full frame",len(buf))
        if buf.startswith(b'\xff\xd8'):
            if self.output is not None:
                self.output.close()
            filename=time.strftime("/var/www/html/imgs/%Y%m%dT%H%M%S.jpg", time.gmtime())
            self.output=open(filename,"wb")
        else:
               print("partial!")
        return self.output.write(buf)


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_POST(self):
        p=urlparse(self.path)
        form=FieldStorage(fp=self.rfile,
                          headers=self.headers,
                          environ={
                              'REQUEST_METHOD': 'POST',
                              'CONTENT_TYPE': self.headers['Content-Type'],
                          }
        )

        print("POST",self.path)
        print(form)
        if p.path == '/action':
            actionid=form.getvalue("id",None)
            if actionid == "starttimelapse":
                c.starttimelapse()
            elif actionid == "startstreaming":
                c.startstreaming()
            elif actionid == "startfocusstreaming":
                c.startstreaming(zoom=3)
            elif actionid == "focusTL":
                c.startstreaming(zoom=3,x='l',y='t')
            elif actionid == "focusTC":
                c.startstreaming(zoom=3,x='c',y='t')
            elif actionid == "focusTR":
                c.startstreaming(zoom=3,x='r',y='t')
            elif actionid == "focusCL":
                c.startstreaming(zoom=3,x='l',y='c')
            elif actionid == "focusCC":
                c.startstreaming(zoom=3,x='c',y='c')
            elif actionid == "focusCR":
                c.startstreaming(zoom=3,x='r',y='c')
            elif actionid == "focusBL":
                c.startstreaming(zoom=3,x='l',y='b')
            elif actionid == "focusBC":
                c.startstreaming(zoom=3,x='c',y='b')
            elif actionid == "focusBR":
                c.startstreaming(zoom=3,x='r',y='b')
            elif actionid == "stop":
                c.stop()

        self.send_response(301)
        self.send_header('Location', '/index.html')
        self.end_headers()
    
    def do_GET(self):
        p=urlparse(self.path)
        print(p)
        if p.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif p.path == '/action':
            q=parse_qs(p.query)
            actionid=q.get("id")[0]
            print(actionid)
            if actionid == "starttimelapse":
                c.starttimelapse()
            elif actionid == "startstreaming":
                c.startstreaming()
            elif actionid == "stop":
                c.stop()
                
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif p.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif p.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

class CameraHandler:
    def __enter__(self):
        return self

    def finalize(self):
        print('Finalizing the Class')
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize()
        
    def __init__(self):
        self.camera=picamera.PiCamera() 

        self.mode=0 ## 0 off 1 streaming 2 timelaps

    def startstreaming(self,zoom=1,x='c',y='c'):
        self.stop()
        self.mode=1
        self.camera.resolution=(self.camera.MAX_RESOLUTION.width//4,self.camera.MAX_RESOLUTION.height//4)
        zw=1/zoom
        zh=1/zoom
        if x=='l':
            zx=0
        elif x=='r':
            zx=1-zw
        else:
            zx=(1-zw)/2

        if y=='t':
            zy=0
        elif y=='b':
            zy=1-zh
        else:
            zy=(1-zh)/2
            
        self.camera.zoom=(zx,zy,zw,zh)
        print("zoom",self.camera.zoom)
        self.camera.framerate=4
        #output = StreamingOutput(self.camera)
        self.camera.start_recording(output, format='mjpeg')

    def stopstreaming(self):
        self.camera.stop_recording()
        self.mode=0

    def tlthread(self):
        interval=5
        nowtime=time.time()
        nexttime=nowtime+5
        # timestamp each file
        filenametemplate="/var/www/html/imgs/image-{timestamp:%Y%m%dT%H%M%S}.jpg"
        
        # make a folder and put in numbered images
        timestamp=datetime.now()
        folder=f"/var/www/html/imgs/{timestamp:%Y%m%dT%H%M%S}"
        os.makedirs(folder, exist_ok=True)
        filenametemplate=folder+"/image-{counter:06d}.jpg"
        
        for filename in self.camera.capture_continuous(filenametemplate):
            #print(filename)
            os.symlink(filename,"/var/www/html/imgs/latest.jpg.new")
            os.rename("/var/www/html/imgs/latest.jpg.new","/var/www/html/imgs/latest.jpg")
            with open(filename,"rb") as f:
                output.write(f.read())
            nexttime+=interval
            nowtime=time.time()
            if (nowtime<nexttime):
                time.sleep(nexttime-nowtime)
            if self.stoptl:
                break;
        
    def starttimelapse(self):
        self.stop()
        self.mode=2
        self.stoptl=False
        self.camera.resolution=self.camera.MAX_RESOLUTION
        self.camera.zoom=(0,0,1,1)
        self.camera.framerate=1/5
        self.tlthread=Thread(target=self.tlthread)
        self.tlthread.start()

    def stoptimelapse(self):
        self.stoptl=True
        self.tlthread.join()
        self.tlthread=None
        self.mode=0
        
    def stop(self):
        if self.mode==1:
            self.stopstreaming()
        elif self.mode==2:
            self.stoptimelapse()



    def close():
        stop()

output=StreamingOutput()
            
with CameraHandler() as c:
    c.startstreaming()
    
    try:
        address = ('', 8000)
        server = StreamingServer(address, StreamingHandler)
        server.serve_forever()


    finally:
        c.stop()


        
        
#with picamera.PiCamera(resolution='1640x922', framerate=12,sensor_mode=5) as camera:
# with picamera.PiCamera() as camera:
#     print(camera.MAX_RESOLUTION)
#     camera.resolution=camera.MAX_RESOLUTION
#     camera.framerate=4
#     camera.exposure_mode='verylong'
#     output = StreamingOutput(camera)
#     fileoutput = FileOutput()
#     print(camera.sensor_mode)
#     #Uncomment the next line to change your Pi's Camera rotation (in degrees)
#     #camera.rotation = 90
#     camera.start_recording(fileoutput, format='mjpeg',splitter_port=2)
#     camera.start_recording(output, format='mjpeg',resize=(camera.MAX_RESOLUTION.width/4,camera.MAX_RESOLUTION.height/4))
#     try:
#         address = ('', 8000)
#         server = StreamingServer(address, StreamingHandler)
#         server.serve_forever()
#     finally:
#         camera.stop_recording()

