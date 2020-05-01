#!/usr/bin/python3

import ctypes
from numpy.ctypeslib import ndpointer
import numpy
lib = ctypes.cdll.LoadLibrary("./libfunpack.so")
_funpack = lib.Unpack_Bayer
_funpack.restype = None
#_funpack.argtypes = [ctypes.c_char_p,
#                ndpointer(ctypes.c_ushort, flags="C_CONTIGUOUS"),
#                ctypes.c_size_t,
#                ctypes.c_size_t,
#                ctypes.c_size_t
#                ]
_funpack.argtypes = [ndpointer(ctypes.c_uint8, flags="C_CONTIGUOUS"),
                ndpointer(ctypes.c_ushort, flags="C_CONTIGUOUS"),
                ctypes.c_size_t,
                ctypes.c_size_t,
                ctypes.c_size_t
                ]
                
def fastunpacker(inputbuffer, outputnumpy, rowstride, rowlen, rowcount):
    assert outputnumpy.dtype==numpy.uint16
    assert rowlen*5 < rowstride
    _funpack(inputbuffer, outputnumpy, rowstride, rowlen, rowcount) 

def testit():
    indata = b'\x01\x02\x03\x04\x00\x01\x02\x03\x04\x03\x01\x02\x03\x04\x0c\x01\x02\x03\x04\x30\xff\xff\xff'*3
    print(len(indata)/3,3)
    outdata = numpy.zeros(shape=(16*3,), dtype=numpy.uint16)
    fastunpacker(indata, outdata, 23, 4, 3)
    print(indata)
    print(outdata)
