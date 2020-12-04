import random
import binascii
from collections import Counter
import numpy as np
import cv2
import lzma
import os

import bingtile
import misc

# Splits DEM to tiles inside specified quadkeys


# Make a list of quadkeys, base quadkey is topleftmost tile to be reconstructed
# padding fills additional tiles around target qkeys,
# if not padded, edges will go to zero elevation
qkeybase = '102231'
qkeyx,qkeyy,qkeylvl=bingtile.QuadKeyToTileXY(qkeybase)
qkeystoprocess=[]
tilesx=3
tilesy=5
padleft=1
padtop=1
padright=1
padbottom=1
idx=(-1)*padleft
idy=(-1)*padtop
while idy<tilesy+padbottom:
    while tilesx+padright<4:
        qkeystoprocess.append(bingtile.TileXYToQuadKey(qkeyx+idx,qkeyy+idy,qkeylvl))
        idx+=1
    idx=-1
    idy+=1

# Create Global Mapper scripts for tile creation
# Split to multiple files (maxperfile) to enable parallel processing
# one level 6 tile contains 4096 level 12 tiles
# Minlevel and maxlevel equal to export only that level
itr = 0
fileindex = 0
maxperfile = 9000
totalcount = 0
for qket in qkeystoprocess:
    minlevel = 12
    maxlevel = 12
    qkey = qket
    while len(qkey) < minlevel:
        qkey += '0'
    level = len(qkey)
    while level <= maxlevel:
        os.makedirs(os.path.dirname("Tile/"+str(level)+"/"), exist_ok=True)
        while qkey.startswith(qket):
            if itr == 0:
                script = open("tilescript_"+str(fileindex).rjust(3, '0')+".gms", 'w')
                script.write('GLOBAL_MAPPER_SCRIPT VERSION=1.00\n')
                script.write('ENABLE_PROGRESS=YES\n')
                script.write(
                    'IMPORT FILENAME=C:\\karttadata\\eudem\\eudem25.gmc ELEV_UNITS=METERS ELEV_SCALE=4 VOID_ELEV=0.0\n')
                script.write(
                    'IMPORT FILENAME=C:\\karttadata\\ALOS\\alos.gmc ELEV_UNITS=METERS ELEV_SCALE=4 VOID_ELEV=0.0\n')
                script.write(
                    'IMPORT FILENAME=C:\\karttadata\\korkeus.gmc ELEV_UNITS=METERS ELEV_SCALE=4\n')
                script.write(   
                    'IMPORT FILENAME=C:\\karttadata\\korkeus2m.gmc ELEV_UNITS=METERS ELEV_SCALE=4 SAMPLING_METHOD=MED_5X5\n')
                script.write('LOAD_PROJECTION PROJ="EPSG:4326"\n')
                fileindex += 1
            print(qkey)
            totalcount += 1
            txy = bingtile.QuadKeyToTileXY(qkey)
            pxy = bingtile.TileXYToPixelXY(txy[0], txy[1])
            ul = bingtile.PixelXYToLatLong(pxy[0], pxy[1], txy[2])
            pxy = bingtile.TileXYToPixelXY(txy[0]+1, txy[1]+1)
            lr = bingtile.PixelXYToLatLong(pxy[0]-0, pxy[1]-0, txy[2])
            pw = (lr[1]-ul[1])/256
            ph = (ul[0]-lr[0])/256
            west = ul[1]
            north = ul[0]
            east = lr[1]
            south = lr[0]
            script.write('EXPORT_ELEVATION TYPE=BIL USE_UNSIGNED=NO BYTES_PER_SAMPLE=2 SPATIAL_RES='+str(pw)+','+str(ph)+' FORCE_SQUARE_PIXELS=NO ELEV_UNITS=METERS SAMPLING_METHOD=LAYER LAT_LON_BOUNDS=' +
                        str(west)+','+str(south)+','+str(east)+','+str(north)+' FILENAME="C:\\Users\\teemu\\source\\repos\MSFS_CGLTools\\'+'Tile\\'+str(level)+"\\"+"dem_"+qkey+'.rw"\n')
            qkey = misc.QuadKeyIncrement(qkey)
            itr += 1
            if itr == maxperfile-1:
                script.close()
                itr = 0
        level += 1
        qkey = qket
        while len(qkey) < level:
            qkey = qkey+'0'

print(totalcount)
script.close()