#!/usr/bin/env python3

import time

now=time.time()

def timestamp(desc):
	global now
	taken=time.time()-now
	print("%s: %f"%(desc,taken))
	now=time.time()

timestamp("Startup")

import numpy
timestamp("Import numpy")
from PIL import Image, ImageDraw, ImageFont, ImageMath, ImageChops
timestamp("Import PIL")
import cv2
timestamp("Import cv2")
import timelapseutils
timestamp("Import timelapseutils")

testres=(4144,2822)

z=numpy.zeros(testres,numpy.uint16)
z2=numpy.zeros(testres,numpy.uint16)
timestamp("Zeros")

r=numpy.random.random(testres)
r2=numpy.random.random(testres)

timestamp("Random")

r=(65535*r).astype(numpy.uint16)
r2=(65536*r).astype(numpy.uint16)
timestamp("Random2uint16")

t=z+z2
timestamp("Add zeros")

t=r+r2
timestamp("Add random")

t=(r.astype(numpy.uint32)+r2.astype(numpy.uint32)).astype(numpy.uint16)
timestamp("random, convert to 32, add convert to 16")

db=timelapseutils.debayer16to8(t)
timestamp("Simple debayer")

i=Image.fromarray(db, mode="RGB")
timestamp("Simple debayer to PIL image")

i.save("/tmp/test.jpg")
timestamp("Simple debayer to PIL image save jpg")

i.save("/tmp/test.png")
timestamp("Simple debayer to PIL image save png")

cv2.imwrite("/tmp/test.jpg",db)
timestamp("opencv debayer to opencv save jpg")

cv2.imwrite("/tmp/test.png",db)
timestamp("opencv debayer to opencv save png")

db=timelapseutils.cvdebayer16to8(t)
timestamp("opencv debayer")

i=Image.fromarray(db, mode="RGB")
timestamp("opencv debayer to PIL image")

i.save("/tmp/test.jpg")
timestamp("opencv debayer to PIL image save jpg")

i.save("/tmp/test.png")
timestamp("opencv debayer to PIL image save png")

cv2.imwrite("/tmp/test.jpg",db)
timestamp("opencv debayer to opencv save jpg")

cv2.imwrite("/tmp/test.png",db)
timestamp("opencv debayer to opencv save png")

