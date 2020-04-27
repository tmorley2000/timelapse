#!/usr/bin/python3

from PIL import Image,ImageFont,ImageDraw
import numpy
from scipy.ndimage import gaussian_filter,uniform_filter
import pprint
from optparse import OptionParser
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

maxlock=Lock()
npmax=None

def loadnblur(i):
    global npmax,maxlock,options
    print("Starting",i)
    image=Image.open(i)
    image.load()
    np=numpy.array(image)
    if options.backgroundsmooth:
        #np=np.astype(numpy.float)
        np=np.astype(numpy.int16)
        if len(np.shape)==3:
            blurred=numpy.zeros(np.shape,dtype=numpy.int16)
            for p in range(np.shape[2]):
                blurred[:,:,p]=gaussian_filter(np[:,:,p],sigma=20)
                #blurred[:,:,p]=uniform_filter(np[:,:,p],size=20)

            else:
                blurred=gaussian_filter(np,sigma=20)
            np=np-blurred
            np=numpy.clip(np,0,255).astype(numpy.uint8)

    print("Locking",i)
    maxlock.acquire()
    if npmax is None:
        npmax=np
    else:
        npmax=numpy.maximum(npmax,np)
    maxlock.release()
    print("Done",i)

    return True


def main():
    global npmax,maxlock,options
    usage = "usage: %prog [options] text ..."
    parser = OptionParser(usage)
    parser.set_defaults(font="/usr/share/fonts/truetype/ttf-bitstream-vera/VeraBd.ttf")
    parser.set_defaults(fontsize=12)
    parser.set_defaults(text=[])
    parser.set_defaults(widthmultiple=1)
    parser.set_defaults(heightmultiple=1)
    parser.set_defaults(filename="max.jpg")
    parser.add_option("-t", "--text", dest="text",action="append",
                      help="Write output to FILENAME")
    parser.add_option("-f", "--file", dest="filename",
                      help="Write output to FILENAME")
    parser.add_option("--font", dest="font",
		      help=".ttf font filename")
    parser.add_option("--fontsize", dest="fontsize",
		      type="int", help="font size")
    parser.add_option("--widthmultiple", dest="widthmultiple",
		      type="int", help="Ensure text box width multiple of this")
    parser.add_option("--heightmultiple", dest="heightmultiple",
		      type="int", help="Ensure text box height multiple of this")
    parser.add_option("-b", "--backgroundsmooth",
                      action="store_true", dest="backgroundsmooth")
    #parser.add_option("-v", "--verbose",
    #                  action="store_true", dest="verbose")
    #parser.add_option("-q", "--quiet",
    #                  action="store_false", dest="verbose")

    (options, args) = parser.parse_args()
#    if len(args) < 1:
#        parser.error("incorrect number of arguments")

    #data=None
    count=0




    executor=ThreadPoolExecutor(max_workers=4)
    futures = {executor.submit(loadnblur, i): i for i in args}
    executor.shutdown()
#    for i in args:
#        print "Applying",i
#        pool.apply_async(loadnblur,i)



    composite=Image.fromarray(npmax)

    font=ImageFont.truetype(options.font,options.fontsize)

    width=0
    height=0
    image=Image.new("RGB",(width,height+1))
    draw=ImageDraw.Draw(image)

    if len(options.text)>0:
        for line in options.text:
            (w,h)=draw.textsize(line,font=font)
            if width < (w+2):
                newwidth=w+2
            newheight=height+h
            newimage=Image.new("RGB",(newwidth,newheight+1))
            newimage.paste(image,(0,0))

            draw=ImageDraw.Draw(newimage)	
            draw.text((1,height),line,font=font)

            width=newwidth
            height=newheight
            image=newimage

        newheight=(((height+1-1)/options.heightmultiple)+1)*options.heightmultiple
        newwidth=(((width-1)/options.widthmultiple)+1)*options.widthmultiple

        if width!=newwidth or height!=newheight:
            newimage=Image.new("RGB",(newwidth,newheight))
            newimage.paste(image,(0,0))
            image=newimage
    
        composite.paste(image,(0,0))
	
    composite.save(options.filename)

        
	
	
        
if __name__ == "__main__":
    main()
