#!/usr/bin/python

from PIL import Image,ImageFont,ImageDraw
import numpy
from scipy.ndimage import gaussian_filter
import pprint
from optparse import OptionParser

def main():
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
    max=None
    count=0
    for imagename in args:
        count=count+1
        print "Image",count,"of",len(args)
        image=Image.open(imagename)
        image.load()
        #images.append(image)
        np=numpy.array(image)
        print np.shape

        if options.backgroundsmooth:
	    np=np.astype(numpy.float)
            if len(np.shape)==3:
                blurred=numpy.zeros(np.shape)
                for p in range(np.shape[2]):
                    blurred[:,:,p]=gaussian_filter(np[:,:,p],sigma=20)
            else:
	        blurred=gaussian_filter(np,sigma=20)
	    np=np-blurred
	    np=numpy.clip(np,0,255).astype(numpy.uint8)

	if max is None:
            max=np
	else:
	    max=numpy.maximum(max,np)

#	if data is None:
#            data=numpy.expand_dims(np,0)
#	else:
#	    data=numpy.append(data,numpy.expand_dims(np,0),0)

#    size=images[0].size
#    
#    for image in images:
#        if image.size != size:
#            parser.error("incorrect image sizes")
#

#    max=numpy.amax(data,0)
#    print max.shape

    composite=Image.fromarray(max)

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
