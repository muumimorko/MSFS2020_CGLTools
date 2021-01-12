import bingtile
import random
import binascii
from collections import Counter
import cv2
import numpy
import lzma
import os
import math

import misc


def ToTileQKey(level, value):
    qkey = numpy.base_repr(value, 4).rjust(level, '0')
    return qkey


def decompress(src, baseqkey, dst):
    """
    Decompressed SRC cgl that represents BASEQKEY to DST folder    
    """
    # Decompressing all sections from a CGL file
    infile = open(src, 'rb')
    inarr = infile.read()
    headerstart = inarr[36]
    headerlength = int.from_bytes(inarr[40:43], 'little')  # UINT24
    headerarr = inarr[headerstart:headerstart+headerlength]
    prop = inarr[49]
    pb = math.floor(prop / (9 * 5))
    prop = prop-(pb * 9 * 5)
    lp = math.floor(prop / 9)
    lc = math.floor(prop - lp * 9)
    my_filters = [{"id": lzma.FILTER_LZMA1,
                   "preset": lzma.PRESET_DEFAULT, "lc": lc, "lp": lp, "pb": pb}, ]
    headerunlzma = lzma.decompress(
        headerarr, lzma.FORMAT_RAW, None, my_filters)
    if not os.path.exists(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst))
    if(len(headerunlzma) > 0):
        outfile = open(dst+"headerunlzma.bin", "bw")
        outfile.write(headerunlzma)
        outfile.close()
    compressedsizes = []
    uncompressedsizes = []
    headersize = len(headerunlzma)
    # count dwords that have zero value at file start
    # if 2, qkey len = WORD, if 4 OR 6, qkey len = DWORD
    qkeysize = 0
    i = 0
    while True:
        value = int.from_bytes(headerunlzma[i:i+2], 'little')
        i += 2
        if value == 0:
            qkeysize += 2
        else:
            break
    if qkeysize == 6:
        qkeysize = 4
    # Extract tile qkeys #! QKEY LENGTH WORD
    tilecount = int.from_bytes(inarr[32:34], 'little')
    counter = 0
    cbegin = 0
    qkeysinbase10 = []
    qkeys = []
    previousval = 0
    level = 0
    while counter < tilecount:
        val = int.from_bytes(headerunlzma[counter*4:counter*4+4], 'little')
        newval = val+previousval
        if newval >= 268435456:
            level += 1
            newval -= 268435456
        qkeysinbase10.append([level, newval])
        previousval = qkeysinbase10[counter][1]
        qkey = ToTileQKey(level, qkeysinbase10[counter][1])
        if counter == 0 and qkey == '0':
            qkey = ''
        qkeys.append(qkey)
        counter += 1
    startpoints = list(
        misc.find_all(inarr, inarr[headerstart+headerlength:headerstart+headerlength+4]))
    lengths = []
    i = 0
    while i < len(startpoints)-1:
        lengths.append(startpoints[i+1]-startpoints[i])
        i += 1
    lengths.append(len(inarr)-startpoints[-1])
    # extract compressed sizes
    compressedsizes = []
    uncompressedsizes = []
    lastVal = 0
    counter = 0
    tilecount = int.from_bytes(inarr[32:34], 'little')
    cbegin = tilecount*qkeysize
    i = cbegin
    while counter < tilecount:
        val = int.from_bytes(headerunlzma[i:i+2], 'little')
        print(counter)
        print("Delta:"+str(val))
        if val >= 0x8000 and val<0xFF00:
            mult=val-0x8000
            i += 2
            nextVal = int.from_bytes(headerunlzma[i:i+2], 'little')
            val = lastVal + (0x10000 * mult) + nextVal
        elif val >= 0xFF00:
            mult = (0xFFFF - val) + 1
            i += 2
            nextVal = int.from_bytes(headerunlzma[i:i+2], 'little')
            val = lastVal - (0x10000 * mult) + nextVal
        elif val > 0x4000:
            nextVal = val
            subVal = 0x8000 - nextVal
            val = lastVal - subVal
        else:
            nextVal = val
            val = lastVal + nextVal
        i += 2
        print("Newcs:"+str(val))
        compressedsizes.append(val)
        lastVal = val
        counter += 1
    for size in compressedsizes:
        print(size)
    i += 0
    counter = 0
    while counter < tilecount:
        val = int.from_bytes(headerunlzma[i:i+2], 'little')
        if val >= 0x8000:
            mult = val - 0x8000
            i += 2
            nextVal = int.from_bytes(headerunlzma[i:i+2], 'little')
            val = compressedsizes[counter] + (0x10000 * mult) + nextVal
        else:
            nextVal = val
            val = compressedsizes[counter] + nextVal 
        i += 2
        print(val)
        uncompressedsizes.append(val)
        counter += 1
    # decompress files DEM from blob
    i = 0
    datastart = headerstart+headerlength
    dataend = datastart+compressedsizes[i]
    prop = inarr[48]
    pb = math.floor(prop / (9 * 5))
    prop = math.floor(prop-(pb * 9 * 5))
    lp = math.floor(prop / 9)
    lc = math.floor(prop - lp * 9)
    my_filters = [{"id": lzma.FILTER_LZMA1,
                   "preset": lzma.PRESET_DEFAULT, "lc": lc, "lp": lp, "pb": pb}, ]
    dummyhdr = open("misc/dummy.hdr", 'rb')
    dummyarr = dummyhdr.read()
    qkeybase = baseqkey
    qkey = qkeybase
    while i < len(compressedsizes):
        print("Index: "+str(i))
        print("Length:"+str(dataend-datastart))
        # print(dataend)
        # print(i)

        print("datastart: "+f'{datastart:08}' + "end: "+f'{dataend:08}')
        fullqkey = qkeybase+qkeys[i]
        outfile = open(dst+"dem_"+fullqkey+".rw", "wb")
        outsize=0
        if compressedsizes[i]==uncompressedsizes[i]:
            print("No compression")
            print(f"Level {len(fullqkey)}")
            outsize=outfile.write(inarr[datastart:dataend])
        else:
            outsize=outfile.write(lzma.decompress(
            inarr[datastart:dataend], lzma.FORMAT_RAW, None, my_filters)[0:])
        outfile.close()
        # write hdr file
        xyl = bingtile.QuadKeyToTileXY(fullqkey)
        pxy = bingtile.TileXYToPixelXY(xyl[0], xyl[1])
        print(pxy)
        print(xyl)
        platlon = bingtile.PixelXYToLatLong(pxy[0], pxy[1], xyl[2])
        yul = platlon[0]
        xul = platlon[1]
        pxy = bingtile.TileXYToPixelXY(xyl[0]+1, xyl[1]+1)
        platlon = bingtile.PixelXYToLatLong(pxy[0], pxy[1], xyl[2])
        yhep = (yul-platlon[0])/256
        xwdp = (platlon[1]-xul)/256
        xul = xul+(xwdp/2)
        yul = yul-(yhep/2)
        outfile = open(dst+"dem_"+fullqkey+".hdr", "w")
        outfile.write("BYTEORDER      I\n")
        outfile.write("LAYOUT         BIL\n")
        outfile.write("NROWS          257\n")
        outfile.write("NCOLS          257\n")
        outfile.write("NBANDS         1\n")
        if outsize==66056:
            outfile.write("NBITS          8\n")
            outfile.write("BANDROWBYTES   257\n")
            outfile.write("TOTALROWBYTES  257\n")
        elif outsize==132105:
            outfile.write("NBITS          16\n")
            outfile.write("BANDROWBYTES   514\n")
            outfile.write("TOTALROWBYTES  514\n")
        outfile.write("BANDGAPBYTES   0\n")
        outfile.write("NODATA         -9999\n")
        outfile.write("SKIPBYTES      7\n")
        outfile.write("PIXELTYPE      SIGNEDINT\n")
        outfile.write("ULXMAP         "+str(xul)+"\n")
        outfile.write("ULYMAP         "+str(yul) + "\n")
        outfile.write("XDIM           "+str(xwdp)+"\n")
        outfile.write("YDIM           "+str(yhep)+"\n")
        outfile.close()
        i = i+1
        if(i < len(compressedsizes)):
            datastart = dataend
            dataend = dataend+compressedsizes[i]
