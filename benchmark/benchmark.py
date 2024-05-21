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
import sys
sys.path.append("..")
timestamp("Import sys")
import timelapseutils
timestamp("Import timelapseutils")
import simplejpeg
timestamp("Import simplejpeg")

testres=(4144,2822)

z=numpy.zeros(testres,numpy.uint16)
z2=numpy.zeros(testres,numpy.uint16)
timestamp("Alocate 2 zero numpy arrays")

r=numpy.random.random(testres)
r2=numpy.random.random(testres)

timestamp("Allocate 2 random numpy float arrays")

r=(65535*r).astype(numpy.uint16)
r2=(65536*r2).astype(numpy.uint16)
timestamp("Convert random arrays to uint16")

t=z+z2
timestamp("Sum zero arrays")

t=r+r2
timestamp("Sum random arrays")

#https://stackoverflow.com/questions/25485886/how-to-convert-a-16-bit-to-an-8-bit-image-in-opencv

t=numpy.clip(r.astype(numpy.uint32)+r2.astype(numpy.uint32),0,65536).astype(numpy.uint16)
timestamp("Clipped sum in numpy (Convert to uint32, sum, clip, convert to uint16)")

t=cv2.add(r,r2)
timestamp("Clipped sum in opencv")

db=timelapseutils.debayer16to8(t)
timestamp("timelapseutils.debayer16to8 result dimensions "+str(db.shape))

i=Image.fromarray(db, mode="RGB")
timestamp("  then convert to PIL image")

i.save("/tmp/test.jpg")
timestamp("    then save jpg")

i.save("/tmp/test.png")
timestamp("    then savesave png")

cv2.imwrite("/tmp/test.jpg",db)
timestamp("  then opencv save jpg")

cv2.imwrite("/tmp/test.png",db)
timestamp("  then opencv save png")

db=timelapseutils.cvdebayer16to8(t)
timestamp("timelapseutils.cvdebayer16to8 result dimensions "+str(db.shape))

i=Image.fromarray(db, mode="RGB")
timestamp("  then convert to PIL image")

i.save("/tmp/test.jpg")
timestamp("    then save jpg")

i.save("/tmp/test.png")
timestamp("    then savesave png")

cv2.imwrite("/tmp/test.jpg",db)
timestamp("  then opencv save jpg")

cv2.imwrite("/tmp/test.png",db)
timestamp("  then opencv save png")

sys.exit(0)

## Some benchmerk test for pi camera stuff
# pi camera 2 generates 10237440 bytes
# 2480  rows of 4128 
# only care about 2464 rows of 4100 
# from https://www.raspberrypi.org/forums/viewtopic.php?t=191114
pibayer=(numpy.random.random(10237440)*256).astype(numpy.uint8)
timestamp("pibayer create random")

rd=pibayer.reshape((2480, 4128))[:2464, :4100]

timestamp("pibayer reshape and crop")

msbs = numpy.delete(rd, numpy.s_[4::5], 1)
print(msbs[0:6,0:6])
timestamp("pibayer simple strip to uint8")

rawimg = rd.astype(numpy.uint16) << 2
for byte in range(4):
    rawimg[:, byte::5] |= ((rawimg[:, 4::5] >> ((4 - byte) * 2)) & 0b11)
rawimg = numpy.delete(rawimg, numpy.s_[4::5], 1)
print(rawimg[0:6,0:6])
timestamp("pibayer simple unpack to uint16")

cells = numpy.empty((rd.shape[0],round(rd.shape[1]/5*4)),dtype=numpy.uint16)
for byte in range(4):
    cells[:, byte::4] = ((rd[:, 4::5] >> ((3 - byte) * 2)) & 0b11)
r1 = rd.astype(numpy.uint16)
for byte in range(4):
    cells[:, byte::4] += r1[:, byte::5] << 2

print(cells[0:6,0:6])
timestamp("pibayer faster unpack to uint16")

## From https://android.googlesource.com/platform/cts/+/master/apps/CameraITS/pymodules/its/image.py
#
#img=rd
#w = int(img.shape[1]*4/5)
#h = img.shape[0]
## Cut out the 4x8b MSBs and shift to bits [9:2] in 16b words.
#msbs = numpy.delete(img, numpy.s_[4::5], 1)
#msbs = msbs.astype(numpy.uint16)
#msbs = numpy.left_shift(msbs, 2)
#msbs = msbs.reshape(h,w)
## Cut out the 4x2b LSBs and put each in bits [1:0] of their own 8b words.
#lsbs = img[::, 4::5].reshape(h,w>>2)
#lsbs = numpy.right_shift(
#       numpy.packbits(numpy.unpackbits(lsbs).reshape(h,w>>2,4,2),3), 6)
## Pair the LSB bits group to 0th pixel instead of 3rd pixel
#lsbs = lsbs.reshape(h,w>>2,4)[:,:,::-1]
#lsbs = lsbs.reshape(h,w)
## Fuse the MSBs and LSBs back together
#img16 = numpy.bitwise_or(msbs, lsbs).reshape(h,w)
#
#print(img16[0:6,0:6])
#timestamp("pibayer slower! unpack to uint16")

import fastunpack

timestamp("pibayer import fastunpack")

outdata = numpy.zeros(shape=(3280*2464), dtype=numpy.uint16)
fastunpack.fastunpacker(pibayer,outdata,4128,820,2464)
outdata=outdata.reshape([2464, 3280])
print(outdata[0:6,0:6])
timestamp("pibayer fastunpack")

#outdata = numpy.zeros(shape=(3280*2464), dtype=numpy.uint16)
#indata=rd.reshape((2464*4100,))
#outview=outdata.view(dtype=numpy.uint64)
##outview|=indata[0::5]<<2
##outview|=indata[1::5]<<18
##outview|=indata[2::5]<<34
##outview|=indata[3::5]<<50
##outview|=(indata[0::5]<<2) |(indata[1::5]<<18) |(indata[2::5]<<34) |(indata[3::5]<<50)
##outview|=(0x4*indata[0::5]) | (0x40000*indata[1::5]) | (0x400000000*indata[2::5]) | (0x4000000000000*indata[3::5])
#outview=numpy.left_shift(indata[0::5],2,dtype=numpy.uint64)|numpy.left_shift(indata[1::5],18,dtype=numpy.uint64)|numpy.left_shift(indata[2::5],34,dtype=numpy.uint64)|numpy.left_shift(indata[3::5],50,dtype=numpy.uint64)
#outview|=(numpy.multiply(indata[4::5],0x0040001000040001,dtype=numpy.uint64)>>6)&0x0003000300030003
#
#outdata=outview.view(dtype=numpy.uint16)
#print(outdata[0:6])
#timestamp("pibayer fast numpy")

