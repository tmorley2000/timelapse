#include <stdint.h>

/*
derived from sample code by user bitbank on the raspberry Pi forums:
    https://www.raspberrypi.org/forums/viewtopic.php?f=43&t=191114

gcc fastunpack.c -c
gcc -shared -o libfunpack.so fastunpack.o

*/
void Unpack_Bayer(const uint8_t *pSrc, uint8_t *pDest, int rowstride, int rowlen, int rowcount)
/*
pSrc        is input raw data - bytes of size rowstride * rowcount + any end padding which is ignored
pDest       is output data - 16 bit unsigned ints of size 4 * rowlen * rowcount
rowstride   is the number of bytes per row - allows for padding bytes on the end of each row
rowlen      is the number of 5 byte groups - each of which is unpacked into 4 ints
rowcount    is the number of rows 
*/
{
const uint32_t u32Magic = 0x40001; // bit expansion multiplier (2 pairs of bits at a time)
const uint32_t u32Mask = 0x30003;  // mask to preserve lower 2 bits of expanded values
uint32_t u32Temp, u32_01, u32_23, *pu32;
int rowpad;
int rctr;
int qctr;
    pu32=(uint32_t *)pDest;
    rowpad=rowstride-rowlen*5;
    for (rctr=0; rctr<rowcount; rctr++)
    {
        for (qctr=0; qctr< rowlen; qctr++)
        {
            u32_01 = (*pSrc++ << 2);
            u32_01 |= (*pSrc++ << 18);     // each 32-bit value will hold 2 source bytes spread out to 16-bits
            u32_23 = (*pSrc++ << 2);       // and shifted over 2 to make room for lower 2 bits
            u32_23 |= (*pSrc++ << 18);
            u32Temp = *pSrc++ *u32Magic;
            u32_23 |= (u32Temp>>2) & u32Mask;   
            u32_01 |= (u32Temp>>6) & u32Mask;         
            *pu32++ = u32_01; // store 4 16-bit pixels (10 significant bits)
            *pu32++ = u32_23;  
        }
        pSrc += rowpad;
    }
}
