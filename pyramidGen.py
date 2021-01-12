from bingtile import *
import numpy as np
import cv2
import multiprocessing as mp
from misc import chunks
import os
import struct

def loadToNPArray(qkey, basepath):
    beginningcoords = QuadKeyToTileXY(qkey+'0')
    xoffset = -1
    yoffset = -1
    loadingarr = np.zeros((1024, 1024), np.int16)
    found = False
    while yoffset < 3:
        while xoffset < 3:
            subqkey = TileXYToQuadKey(
                beginningcoords[0]+xoffset, beginningcoords[1]+yoffset, beginningcoords[2])
            if os.path.isfile(basepath+"\\Tile/"+str(len(subqkey))+"/dem"+subqkey+".bil"):
                infile = open(basepath+"\\Tile/"+str(len(subqkey)) +
                              "/dem"+subqkey+".bil", 'rb')
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


def createLevelTileAndSubDeltas(qkey, basepath):
    found, nparrupper = loadToNPArray(qkey, basepath)
    if found:
        down = np.zeros((512, 512), np.int16)
        blur = cv2.GaussianBlur(nparrupper, (9, 9), 32)
        #blur = cv2.blur(nparrupper,(5,5))
        #kernel = np.ones((7,7),np.float32)/(7*7)
        #blur = cv2.filter2D(nparrupper,-1,kernel)
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
        saveTile(basepath+"\\Tile", qkey, downpadded)
        up = np.zeros((1024, 1024), np.int16)
        # up=blur
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
        saveDelta(basepath+"\\Delta", qkey+str(0), delta0, 1, 0)
        saveDelta(basepath+"\\Delta", qkey+str(1), delta1, 1, 0)
        saveDelta(basepath+"\\Delta", qkey+str(2), delta2, 1, 0)
        saveDelta(basepath+"\\Delta", qkey+str(3), delta3, 1, 0)


def saveTile(type, qkey, data):
    filename = type+"\\"+str(len(qkey))+"\\"+"dem"+qkey+".bil"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    outfile = open(filename, 'wb')
    outfile.write(data)
    outfile.close()


def saveDelta(type, qkey, data, multi, offsetm):
    offset = (math.floor(offsetm/multi)).to_bytes(2, 'little', signed=True)
    heightscale = bytearray(struct.pack("f", multi))
    header = bytes(heightscale)+offset+(16).to_bytes(1, 'little')
    filename = type+"\\"+str(len(qkey))+"\\"+"dem"+qkey+".bil"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    outfile = open(filename, 'wb')
    outfile.write(header)
    outfile.write(data)
    outfile.close()


def to8bit(qkey, basepath):
    infile = open(basepath+"\\Tile/"+str(len(qkey))+"/dem"+qkey+".bil", 'rb')
    basetile0 = infile.read()
    infile.close()
    nparr = np.frombuffer(basetile0, np.int16).reshape((257, 257))
    saveDelta(basepath+"\\Tile", qkey, nparr, 1, 0)


def createLevelTileAndSubDeltasChunk(idx, chk, basepath):
    for qkey in chk:
        createLevelTileAndSubDeltas(qkey, basepath)
    return 'OK'


def collect_result(result):
    return


def createPyramids(TopLevelQKeys, options):
    print("Generating pyramids")
    minlevel = options.CGLLevel
    maxlevel = options.MaxLevel-1
    level = maxlevel
    while level >= minlevel:
        subqkeys = []
        for qKey in TopLevelQKeys:
            qKey = qKey[0]
            qkey = qKey
            while len(qkey) < level:
                qkey = qkey+'0'
            while qkey.startswith(qKey):
                subqkeys.append(qkey)
                qkey = QuadKeyIncrement(qkey)
        threads = options.ProcessingThreads
        tilesPerPart = int(len(subqkeys)/(4*threads))
        if tilesPerPart == 0:
            tilesPerPart = 1
        if len(subqkeys)/tilesPerPart < threads:
            threads = int(len(subqkeys)/tilesPerPart)
        subchunks = chunks(subqkeys, tilesPerPart)
        pool = mp.Pool(threads)
        print("Processing level " + str(level).rjust(2, '0') + ", Threads " + str(threads).rjust(2,
                                                                                                 '0') + ", TPP "+str(tilesPerPart).rjust(2, '0') + ", Total tiles: " + str(len(subqkeys)))
        for idx, chunk in enumerate(subchunks):
            pool.apply_async(createLevelTileAndSubDeltasChunk, args=(
                idx, chunk, options.Basepath), callback=collect_result)
        pool.close()
        pool.join()
        level -= 1
    for qKey in TopLevelQKeys:
        to8bit(qKey[0], options.Basepath)