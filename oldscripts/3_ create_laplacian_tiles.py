import multiprocessing as mp
import numpy as np
import cv2
import os
import misc
import struct
import bingtile
from matplotlib import pyplot as plt
import math


def loadToNPArray(qkey):
    beginningcoords = bingtile.QuadKeyToTileXY(qkey+'0')
    xoffset = -1
    yoffset = -1
    loadingarr = np.zeros((1024, 1024), np.int16)
    found = False
    while yoffset < 3:
        while xoffset < 3:
            subqkey = bingtile.TileXYToQuadKey(
                beginningcoords[0]+xoffset, beginningcoords[1]+yoffset, beginningcoords[2])
            if os.path.isfile("Tile/"+str(len(subqkey))+"/dem_"+subqkey+".rw"):
                infile = open("Tile/"+str(len(subqkey)) +
                              "/dem_"+subqkey+".rw", 'rb')
                tilearr = infile.read()
                infile.close()
                nparr = np.frombuffer(tilearr, np.int16).reshape((257, 257))
                x_offset = (xoffset+1)*256
                y_offset = (yoffset+1)*256
                loadingarr[y_offset:y_offset+nparr.shape[0]-1,
                           x_offset:x_offset+nparr.shape[1]-1] = nparr[0:256, 0:256]
                found = True
            xoffset += 1
        xoffset = -1
        yoffset += 1
    return found, loadingarr


def createLevelTileAndSubDeltas(qkey):
    found, nparrupper = loadToNPArray(qkey)
    if found:
        down = np.zeros((512, 512), np.int16)
        blur = cv2.GaussianBlur(nparrupper, (9, 9), 32)
        itrr = 0
        itrc = 0
        while itrc < 512:
            while itrr < 512:
                down[itrc, itrr] = blur[itrc*2, itrr*2]
                itrr += 1
            itrr = 0
            itrc += 1
        downpadded = np.zeros((257, 257), np.int16)
        downpadded[0:257, 0:257] = down[128:128+257, 128:128+257]
        saveTile("Tile", qkey, downpadded)
        up = np.zeros((1024, 1024), np.int16)
        up = cv2.pyrUp(down)
        delta = np.zeros((512, 512), np.int16)
        delta = np.subtract(nparrupper, up)
        delta0 = np.zeros((257, 257), np.int16)
        delta0[0:257, 0:257] = delta[256:+256+257, 256:256+257]
        delta1 = np.zeros((257, 257), np.int16)
        delta1[0:257, 0:257] = delta[256:+256+257, 512:512+257]
        delta2 = np.zeros((257, 257), np.int16)
        delta2[0:257, 0:257] = delta[512:512+257, 256:256+257]
        delta3 = np.zeros((257, 257), np.int16)
        delta3[0:257, 0:257] = delta[512:512+257, 512:512+257]
        saveDelta("Delta", qkey+str(0), delta0, 1/1, 0)
        saveDelta("Delta", qkey+str(1), delta1, 1/1, 0)
        saveDelta("Delta", qkey+str(2), delta2, 1/1, 0)
        saveDelta("Delta", qkey+str(3), delta3, 1/1, 0)


def saveTile(type, qkey, data):
    filename = type+"\\"+str(len(qkey))+"\\"+"dem_"+qkey+".rw"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    outfile = open(filename, 'wb')
    outfile.write(data)
    outfile.close()


def saveDelta(type, qkey, data, multi, offsetm):
    offset = (math.floor(offsetm/multi)).to_bytes(2, 'little', signed=True)
    heightscale = bytearray(struct.pack("f", multi))
    header = bytes(heightscale)+offset+(16).to_bytes(1, 'little')
    filename = type+"\\"+str(len(qkey))+"\\"+"dem_"+qkey+".rw"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    outfile = open(filename, 'wb')
    outfile.write(header)
    outfile.write(data)
    outfile.close()


def to8bit(qkey):
    infile = open("Tile/"+str(len(qkey))+"/dem_"+qkey+".rw", 'rb')
    basetile0 = infile.read()
    infile.close()
    nparr = np.frombuffer(basetile0, np.int16).reshape((257, 257))
    saveDelta("Tile", qkey, nparr, 1/1, -47)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def createLevelTileAndSubDeltasChunk(idx, chk):
    for qkey in chk:
        createLevelTileAndSubDeltas(qkey)
    return 'OK'


def collect_result(result):
    return


px,py=bingtile.LatLongToPixelXY(51.9593211025, -3.0832820611,6)
tx,ty=bingtile.PixelXYToTileXY(px,py)
qkeybase = bingtile.TileXYToQuadKey(tx,ty,6)
qkeyx,qkeyy,qkeylvl=bingtile.QuadKeyToTileXY(qkeybase)
qkeystoprocess=[]
tilesx=1
tilesy=1
padleft=0
padtop=0
padright=0
padbottom=0
idx=(-1)*padleft
idy=(-1)*padtop
while idy<tilesy+padbottom:
    while idx<tilesx+padright:
        qkeystoprocess.append(bingtile.TileXYToQuadKey(qkeyx+idx,qkeyy+idy,qkeylvl))
        idx+=1
    idx=padleft
    idy+=1

minlevel = 6
maxlevel = 11
level = maxlevel
if __name__ == '__main__':
    while level >= minlevel:
        for qk in qkeystoprocess:
            subqkeys = []
            qkey = qk
            while len(qkey) < level:
                qkey = qkey+'0'
            while qkey.startswith(qk):
                print(qkey)
                subqkeys.append(qkey)
                qkey = misc.QuadKeyIncrement(qkey)
            parts = int(len(subqkeys)/32)
            if parts == 0:
                parts = 1
            subchunks = chunks(subqkeys, parts)
            pool = mp.Pool(int(mp.cpu_count()/1))
            for idx, chunk in enumerate(subchunks):
                pool.apply_async(createLevelTileAndSubDeltasChunk, args=(
                    idx, chunk), callback=collect_result)
            pool.close()
            pool.join()
        level -= 1
    for qk in qkeystoprocess:
        to8bit(qk)
