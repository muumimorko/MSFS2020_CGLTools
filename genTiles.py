import copy
from xml.dom import minidom
from xml.etree import ElementTree
import matplotlib.pyplot as plt
import xml
from xml.etree.ElementTree import Element, SubElement, Comment
from datetime import datetime
from calendar import timegm
from bingtile import LatLongToTileXY, TileXYToQuadKey, PixelXYToLatLong, TileXYToPixelXY, QuadKeyToTileXY
from misc import QuadKeyIncrement, chunks
from dataclasses import dataclass
from typing import Any
import os
import statistics
import time
import glob
import shapefile
import subprocess
import click
import multiprocessing as mp
import numpy as np
import cv2
import struct
from matplotlib import pyplot as plt
import math
import json
from shutil import copyfile
import gdal
from pyproj import pyproj, Proj, Transformer


def TileXYsToQkeys(tileXY_UL, tileXY_LR, options):
    padding = options.padding
    CGLLevel = options.CGLLevel
    xmin = tileXY_UL[0]-padding
    ymin = tileXY_UL[1]-padding
    xmax = tileXY_LR[0]+padding
    ymax = tileXY_LR[1]+padding
    x = xmin
    y = ymin
    qKeys = []
    while y <= ymax:
        while x <= xmax:
            if y >= tileXY_UL[1] and y <= tileXY_LR[1] and x >= tileXY_UL[0] and x <= tileXY_LR[0]:
                qKeys.append([TileXYToQuadKey(x, y, CGLLevel), 0])
            else:
                qKeys.append([TileXYToQuadKey(x, y, CGLLevel), 1])
            x += 1
        x = xmin
        y += 1
    return qKeys


def CoordsToQkeyList(latLongUL, latLongLR, options):
    CGLLevel = options.CGLLevel
    tileXY_UL = LatLongToTileXY(latLongUL, CGLLevel)
    tileXY_LR = LatLongToTileXY(latLongLR, CGLLevel)
    qKeys = TileXYsToQkeys(tileXY_UL, tileXY_LR, options)
    return qKeys


def SubtileCount(baselevel, minlevel, MaxLevel):
    count = 0
    level = minlevel
    while level <= MaxLevel:
        count += pow(4, level-baselevel)
        level += 1
    return count


def ListSubQKeys(qKey, level):
    subQKey = qKey
    subQKeys = []
    while len(subQKey) < level:
        subQKey += '0'
    while subQKey.startswith(qKey):
        subQKeys.append(subQKey)
        subQKey = QuadKeyIncrement(subQKey)
    return subQKeys


def ListAllSubQKeys(TopLevelQKeys, level, basepath):
    AllSubQKeys = []
    os.makedirs(os.path.dirname(
        basepath+"/Tile/"+str(level)+"/"), exist_ok=True)
    for qKey in TopLevelQKeys:
        AllSubQKeys.extend(ListSubQKeys(qKey[0], level))
    return AllSubQKeys


def qKeyToBoundingLatLong(qKey):
    txy = QuadKeyToTileXY(qKey)
    pxy = TileXYToPixelXY(txy[0], txy[1])
    ul = PixelXYToLatLong(pxy[0], pxy[1], txy[2])
    pxy = TileXYToPixelXY(txy[0]+1, txy[1]+1)
    lr = PixelXYToLatLong(pxy[0]+0, pxy[1]+0, txy[2])
    west = ul[1]
    north = ul[0]
    east = lr[1]
    south = lr[0]
    return west, north, east, south


def PixelDimensions(east, west, north, south, pixels):
    pw = (east-west)/pixels
    ph = (north-south)/pixels
    return pw, ph


def CreateGlobalMapperScript(index, subQKeys, options):
    script = open(options.Basepath+"/tilescript_" +
                  str(index).rjust(3, '0')+".gms", 'w')
    script.write('GLOBAL_MAPPER_SCRIPT VERSION=1.00\n')
    for path in options.DEMInputFiles:
        script.write('IMPORT FILENAME=\"'+path +
                     '" ELEV_UNITS=METERS ELEV_SCALE=1\n')
    script.write('LOAD_PROJECTION PROJ="EPSG:4326"\n')
    for subQKey in subQKeys:
        west, north, east, south = qKeyToBoundingLatLong(subQKey)
        pw, ph = PixelDimensions(east, west, north, south, 256)
        level = len(subQKey)
        script.write('EXPORT_ELEVATION TYPE=BIL USE_UNSIGNED=NO BYTES_PER_SAMPLE=2 SPATIAL_RES='+str(pw)+','+str(ph)+' FORCE_SQUARE_PIXELS=NO ELEV_UNITS=METERS SAMPLING_METHOD=LAYER LAT_LON_BOUNDS=' +
                     str(west)+','+str(south)+','+str(east)+','+str(north)+' FILENAME="'+os.path.abspath(options.Basepath)+'\\Tile\\'+str(level)+"\\"+"dem"+subQKey+'.bil"\n')
    script.close()


#! Not in use, do elevation correction before executing this script
def GMCreateUndulatedSource(index, subQKeys, options):
    script = open(options.Basepath+"/undulatescript_" +
                  str(index).rjust(3, '0')+".gms", 'w')
    script.write('GLOBAL_MAPPER_SCRIPT VERSION=1.00\n')
    script.write(
        'IMPORT FILENAME=\"C:\\test\\und_egm2008_wgs84.bil\" ELEV_UNITS=METERS ELEV_SCALE=1\n')
    for path in options.DEMInputFiles:
        script.write('IMPORT FILENAME=\"'+path +
                     '" ELEV_UNITS=METERS ELEV_SCALE=1\n')

    script.write('LOAD_PROJECTION PROJ="EPSG:4326"\n')
    for subQKey in subQKeys:
        west, north, east, south = qKeyToBoundingLatLong(subQKey[0])
        level = len(subQKey[0])
        script.write('COMBINE_TERRAIN COMBINE_OP=ADD LAT_LON_BOUNDS=' +
                     str(west)+','+str(south)+','+str(east)+','+str(north)+'\n')
        script.write('EXPORT_ELEVATION TYPE=BIL USE_UNSIGNED=NO BYTES_PER_SAMPLE=2 '+'FORCE_SQUARE_PIXELS=NO ELEV_UNITS=METERS SAMPLING_METHOD=LAYER LAT_LON_BOUNDS=' +
                     str(west)+','+str(south)+','+str(east)+','+str(north)+' FILENAME="'+os.path.abspath(options.Basepath)+'\\UndulatedSRC\\'+"dem"+subQKey[0]+'.bil"\n')
    script.close()


def StartGMScripts(basepath):
    files = glob.glob(basepath+r'\tilescript*.gms')
    for file in files:
        os.system(file)


def MonitorTileCreation(basepath, totalTileCount):
    # Monitor tile creation process
    deltas = []
    previous = 0
    while True:
        count = len(glob.glob(basepath+"/Tile/*/*.bil"))
        if previous == 0:
            previous = count
        else:
            delta = count-previous
            deltas.append(delta)
            if len(deltas) > 30:
                deltas.pop(0)
            avg = statistics.mean(deltas)
            left = totalTileCount-count
            previous = count
            if avg > 0:
                secondsleft = left/avg
            else:
                secondsleft = -1
            print("Done: " + str(count).rjust(7, '0')+" of " +
                  str(totalTileCount) + " Time left: " + f"{secondsleft:.0f}")
            time.sleep(1)
            if count == totalTileCount or (count > 1 and secondsleft == -1):
                break
    print("Tiles generated")


def createCoveragePolyShapefile(qKeys, basepath):
    w = shapefile.Writer(basepath+r'\qKeyCoverage.shp')
    w.field('name', 'C')
    w.field('paddingtile', 'L')
    for qKey in qKeys:
        west, north, east, south = qKeyToBoundingLatLong(qKey[0])
        w.poly([[[west, north], [east, north], [east, south], [west, south]]])
        w.record(qKey[0], qKey[1])
    w.close()


def createGMVisualizationScript(options):
    script = open(Options.Basepath+"/visualize.gmw", 'w')
    script.write('GLOBAL_MAPPER_SCRIPT VERSION=1.00\n')
    for path in options.DEMInputFiles:
        script.write('IMPORT FILENAME=\"'+path +
                     '" ELEV_UNITS=METERS ELEV_SCALE=1\n')
    script.write('IMPORT FILENAME=\"'+Options.Basepath +
                 '\\qKeyCoverage.shp" LABEL_FIELD="name" PROJ="EPSG:4326"\n')


def visualize(exepath, basepath):
    process = subprocess.Popen(
        "\""+exepath + "\" " + basepath+'\\visualize.gmw', shell=True, stdout=subprocess.PIPE)
    process.wait()


def calculateMaxDiskUsageMB(qKeyCount, options):
    singleQKeyTiles = SubtileCount(
        options.CGLLevel, options.CGLLevel, options.MaxLevel)
    singleQKeyDeltas = SubtileCount(
        options.CGLLevel, options.CGLLevel+1, options.MaxLevel)
    totalFileCount = qKeyCount*singleQKeyTiles+qKeyCount*singleQKeyTiles
    totalSize = totalFileCount*132098/1048576+(qKeyCount*2*100)
    return totalSize


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


def createCGLs(TopLevelQKeys, basepath):
    totalcount = 0
    for qkey in TopLevelQKeys:
        if qkey[1] == False:
            totalcount += 1
    print("Generating "+str(totalcount)+" CGLs")
    counter = 0
    for qkey in TopLevelQKeys:
        if qkey[1] == False:
            files = glob.glob(basepath+"\\Tile/6/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/7/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/8/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/9/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/10/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/11/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/12/dem"+qkey[0]+"*.bil")
            files += glob.glob(basepath+"\\Delta/13/dem"+qkey[0]+"*.bil")
            cglc.createCGL(files, basepath+"\\" +
                           qkey[0][0:3]+"/dem"+qkey[0][3:6]+".cgl")
            counter += 1
            print("Done "+str(counter)+' of '+str(totalcount))


def dt_to_filetime(dt):
    EPOCH_AS_FILETIME = 116444736000000000  # January 1, 1970 as MS file time
    HUNDREDS_OF_NANOSECONDS = 10000000
    return EPOCH_AS_FILETIME + (timegm(dt.timetuple()) * HUNDREDS_OF_NANOSECONDS)


def makePackageFolder(TopLevelQKeys, options, manifest):
    foldername = options.Basepath+"\\"+options.TargetName+"\\"
    os.makedirs(os.path.dirname(foldername), exist_ok=True)
    manifestfile = open(foldername+"manifest.json", 'w')
    manifestfile.write(json.dumps(manifest, indent=4))
    manifestfile.close()
    thumbnail = np.zeros((170, 412, 3), dtype='uint8')
    font = cv2.FONT_HERSHEY_COMPLEX
    cv2.putText(thumbnail, options.TargetName, (10, 95),
                font, 1, (255, 255, 255), 2, cv2.LINE_AA)
    os.makedirs(os.path.dirname(foldername+"ContentInfo\\" +
                                options.TargetName+"\\"), exist_ok=True)
    cv2.imwrite(foldername+"ContentInfo\\" +
                options.TargetName+"\\Thumbnail.jpg", thumbnail)
    layout = {
        "content": [
            {
                "path": "ContentInfo/"+options.TargetName+"/Thumbnail.jpg",
                "size": os.path.getsize(foldername+"ContentInfo\\"+options.TargetName+"\\Thumbnail.jpg"),
                "date": dt_to_filetime(datetime.fromtimestamp(time.time()))
            }
        ]
    }
    for qKey in TopLevelQKeys:
        if qKey[1] == False:
            os.makedirs(os.path.dirname(
                foldername+"CGL\\"+qKey[0][0:3]+"\\"), exist_ok=True)
            copyfile(options.Basepath+"\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6] +
                     ".cgl", foldername+"CGL\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6]+".cgl")
            size = os.path.getsize(
                foldername+"CGL\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6]+".cgl")
            path = os.path.relpath(
                foldername+"CGL\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6]+".cgl", foldername).replace("\\", "/")
            date = dt_to_filetime(datetime.fromtimestamp(time.time()))
            layout["content"].append(
                {"path": path, "size": size, "date": date})
    layoutfile = open(foldername+"layout.json", 'w')
    layoutfile.write(json.dumps(layout, indent=4))
    layoutfile.close()


# Manifest data that will be written to the manifest.json in package folder.
manifest = {
    "dependencies": [],
    "content_type": "SCENERY",
    "title": "Finland",
    "manufacturer": "",
    "creator": "creator",
    "package_version": "0.2.0",
    "minimum_game_version": "1.11.6",
    "release_notes": {
        "neutral": {
            "LastUpdate": "Elevation fixed",
            "OlderHistory": "These can be seen in package manager"
        }
    }
}


@dataclass
# Options for configuring DEM tile and CGL generation
# CGLLevel: Bing maps tile level that will be the lowest resolution
#           in generated CGLs. Default 6.
# MaxLevel: Highest Bing maps tile level used when generating tiles,
#           also DEM tile cutting level. Default 12.
# Padding: If enabled (=1), generates extra tiles around target area
#          to minimize edge errors. Default 1.
# DEMInputFiles: List of source elevation data files,
#                can be any format Global Mapper supports.
# GMExePath: Path to Global Mapper executable.
# GMThreads: How many GM instances to run in parallel
#            to speed up processing.
#            Change based on cpu cores and available memory.
#            Some source material can use gigabytes of memory,
#            while other can use just hundreds of megabytes.
# ProcessingThreads: Laplacian pyramid and GCL compression
#                    parallelization. Default computer thread count.
# BasePath: Path to folder where generated files will go.
#           Default './_temp/' (current_directory/_temp).
# TargetName: Package name for the project.
class Options():
    CGLLevel: int = 8
    MaxLevel: int = 14
    padding: int = 0
    DEMInputFiles = [r'C:\test\und_egm2008_wgs84.bil', r'C:\karttadata\ALOS_egm2008\alos_egm2008.gmc',
                     r'C:\karttadata\korkeusmalli_egm2008\hila10m\10m_egm2008.gmc']
    #DEMInputFiles = [r'C:\karttadata\korkeusmalli_egm2008\hila10m\10m_egm2008.gmc']
    GMExePath: str = r'C:\Program Files\GlobalMapper22.0_64bit\global_mapper.exe'
    GMThreads: int = 16
    ProcessingThreads: int = mp.cpu_count()
    Basepath: str = os.path.abspath('./_temp/')
    TargetName: str = "morko-dem-test-10m"


@dataclass
class LatLong():
    latitude: float = 0
    longitude: float = 0


# https://pymotw.com/2/xml/etree/ElementTree/create.html

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    root = reparsed.childNodes[0]
    root.toprettyxml(encoding="utf-8")
    return reparsed.toprettyxml(indent="  ")


# https://gist.github.com/royshil/0b20a7dd08961c83e210024a4a7d841a


def Laplacian_Pyramid_Blending_with_mask(A, B, m, num_levels=6):
    # assume mask is float32 [0,1]
    # generate Gaussian pyramid for A,B and mask
    GA = A.copy()
    GB = B.copy()
    GM = m.copy()
    gpA = [GA]
    gpB = [GB]
    gpM = [GM]
    for i in [0, 1, 2, 3, 4]:
        GA = cv2.pyrDown(GA)
        GB = cv2.pyrDown(GB)
        GM = cv2.pyrDown(GM)
        gpA.append(np.float32(GA))
        gpB.append(np.float32(GB))
        gpM.append(np.float32(GM))
    # generate Laplacian Pyramids for A,B and masks
    # the bottom of the Lap-pyr holds the last (smallest) Gauss level
    lpA = [gpA[num_levels-1]]
    lpB = [gpB[num_levels-1]]
    gpMr = [gpM[num_levels-1]]
    for i in [4, 3, 2, 1]:
        # Laplacian: subtarct upscaled version of lower level from current level
        # to get the high frequencies
        LA = np.subtract(gpA[i-1], cv2.pyrUp(gpA[i]))
        LB = np.subtract(gpB[i-1], cv2.pyrUp(gpB[i]))
        lpA.append(LA)
        lpB.append(LB)
        gpMr.append(gpM[i-1])  # also reverse the masks
    # Now blend images according to mask in each level
    LS = []
    for la, lb, gm in zip(lpA, lpB, gpMr):
        ls = la * gm + lb * (1.0 - gm)
        LS.append(ls)
    # now reconstruct
    ls_ = LS[0]
    for i in [1, 2, 3, 4]:
        ls_ = cv2.pyrUp(ls_)
        ls_ = cv2.add(ls_, LS[i])
    return ls_


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def compressChunkQKEY(chunks):
    datas = []
    for chunk in chunks:
        west = chunk[1][0]
        north = chunk[1][3]
        south = chunk[1][1]
        east = chunk[1][2]
        # completetile
        geod = pyproj.Geod(ellps='WGS84')
        azimuth1, azimuth2, distance = geod.inv(west, north, east, north)
        kwargs = {'resampleAlg': 'cubic', 'multithread': True, 'format': 'eHDR',  'geoloc': False, 'srcSRS': "+proj=utm +zone=35 +datum=WGS84 +geoidgrids=C:\OSGeo4W64\share\proj\egm08_25.gtx",
                  'dstSRS': "EPSG:4326", 'outputBounds': [west, south, east, north], 'width': 256, 'height': 256}
        ds1 = gdal.Warp(
            '/vsimem/inmem{}H.bil'.format(chunk[0]), r'I:\karttadata\korkeusmalli\combined.vrt', **kwargs)
        nparrH = ds1.ReadAsArray()
        if nparrH.max() != -9999.0:
            # plt.imshow(nparrH)
            # plt.show()
            if nparrH.min() == -9999.0:
                kwargs = {'resampleAlg': 'cubic', 'multithread': True, 'format': 'eHDR',  'geoloc': False, 'srcSRS': "+proj=longlat +datum=WGS84 +geoidgrids=C:\OSGeo4W64\share\proj\egm08_25.gtx",
                          'dstSRS': "EPSG:4326", 'outputBounds': [west, south, east, north], 'width': 256, 'height': 256}
                ds2 = gdal.Warp(
                    '/vsimem/inmem{}L.bil'.format(chunk[0]), r'I:\karttadata\ALOS\alos.vrt', **kwargs)
                nparrL = ds2.ReadAsArray()
                mask = np.where(nparrH == -9999.0,
                                np.float32(0.0), np.float32(1.0))
                nparrC = np.where(nparrH != -9999.0, nparrH, nparrL)
                lpb = Laplacian_Pyramid_Blending_with_mask(
                    nparrC, nparrL, mask, 5)
                nparrH = lpb
                gdal.Unlink('/vsimem/inmem{}L.bil'.format(chunk[0]))
            middlelong = (east+west)/2
            falloff = 20.0
            priority = 20
            latitude = north
            longitude = middlelong
            latitude2 = south
            longitude2 = middlelong
            widthPixels = 256
            data = ""
            avgh = np.average(nparrH)
            altitude = avgh
            altitude2 = altitude
            flipped = np.fliplr(nparrH)
            # plt.imshow(flipped)
            # plt.show()
            for x in flipped:
                for y in x:
                    # if y==-9999:
                    #     plt.imshow(flipped)
                    #     plt.show()
                    data += "{:.5f}".format(y)+" "
            data = data[:-1]
            datas.append({'qkey': chunk[0], 'data': data, 'widthm': distance, 'middlelong': middlelong,
                          'north': latitude, 'south': latitude2, 'altitude': altitude, 'priority': priority})
            gdal.Unlink('/vsimem/inmem{}H.bil'.format(chunk[0]))
    return [datas]


returns = {}
# Step 2: Define callback function to collect the output in `results`


def collect_result(result):
    global returns
    returns[result[0]] = result[1]


def genTiles(idx, subqkeys):
    start = time.time()
    res = compressChunkQKEY(subqkeys)
    result = []
    result.append(res)
    itr = 0
    for rct in result[0][0]:
        top = Element('FSData', version='9.0')
        rect = SubElement(top, 'Rectangle', width=str(rct['widthm']), falloff=str(50), surface="{47D48287-3ADE-4FC5-8BEC-B6B36901E612}", priority=str(rct['priority']
                                                                                                                                                      ), latitude=str(rct['north']), longitude=str(rct['middlelong']), altitude=str(rct['altitude']), latitude2=str(rct['south']), longitude2=str(rct['middlelong']), altitude2=str(rct['altitude']))
        heightmap = SubElement(
            rect, 'Heightmap', width=str(256), data=rct['data'])
        os.makedirs(os.path.dirname(
            f"C:\MyFSProjects\Heightmaps\morko-heightmap-nature\heightmap{str(rct['qkey'])}\{str(rct['qkey'])}.xml"), exist_ok=True)
        outfile = open(
            f"C:\MyFSProjects\Heightmaps\morko-heightmap-nature\heightmap{str(rct['qkey'])}\{str(rct['qkey'])}.xml", 'wb')
        outfile.write(ElementTree.tostring(
            top, encoding='utf8', method='html'))
        outfile.close()
    end = time.time()
    print(end - start)
    return 0


def generateCoverageSourceShapefile(allSubQkeys):
    w = shapefile.Writer(
        r'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\allqkeysl14.shp', shapeType=5)
    w.field('qkey', 'C')
    for qkey in allSubQkeys:
        west, north, east, south = qKeyToBoundingLatLong(qkey)
        w.poly([[[west, north], [east, north], [
               east, south], [west, south], [west, north]]])
        w.record(qkey)
    w.close()


def genPackageDefinitionXML():
    pkglist = glob.glob(
        r'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\heightmap*\*.xml')
    AssetPackage = Element(
        'AssetPackage', Name=f'morko-dem-finland-heightmap-airports', Version='0.1.0')
    ItemSettings = SubElement(AssetPackage, 'ItemSettings')
    ContentType = SubElement(ItemSettings, 'ContentType')
    ContentType.text = "SCENERY"
    Title = SubElement(ItemSettings, 'Title')
    Title.text = "Finland - Heightmaps for airports"
    Manufacturer = SubElement(ItemSettings, 'Manufacturer')
    Creator = SubElement(ItemSettings, 'Creator')
    Creator.text = 'morko'
    Flags = SubElement(AssetPackage, 'Flags')
    VisibleInStore = SubElement(Flags, 'Flags')
    VisibleInStore.text = 'false'
    CanBeReferenced = SubElement(Flags, 'CanBeReferenced')
    CanBeReferenced.text = 'false'
    AssetGroups = SubElement(AssetPackage, 'AssetGroups')
    Agroups = []
    Agroup = ElementTree.fromstring(
        '<AssetGroup Name="ContentInfo"><Type>ContentInfo</Type><Flags><FSXCompatibility>false</FSXCompatibility></Flags><AssetDir>PackageDefinitions\morko-dem-finland-heightmap-airports\ContentInfo</AssetDir><OutputDir>ContentInfo\morko-dem-finland-heightmap-airports</OutputDir></AssetGroup>')
    Agroups.append(copy.deepcopy(Agroup))
    for pkg in pkglist:
        pkg = pkg[-18:-4]
        Agroup.set('Name', f'heightmap-finland-{pkg}')
        Agroup.find('Type').text = 'BGL'
        Agroup.find('AssetDir').text = f'heightmap{pkg}'
        Agroup.find('OutputDir').text = f'scenery\\heightmaps\\finland\\'
        Agroups.append(copy.deepcopy(Agroup))
    AssetGroups.extend(Agroups)
    outfile = open(
        f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\PackageDefinitions\morko-dem-finland-heightmap-airports.xml', 'wb')
    outfile.write(ElementTree.tostring(
        AssetPackage, encoding='utf8', method='html'))
    outfile.close()
    genProjectXML(1)
    genSinglePackageXMLs()


def genSinglePackageXMLs():
    pkglist = glob.glob(
        r'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\heightmap*\*.xml')
    for pkg in pkglist:
        pkg = pkg[-18:-4]
        AssetPackage = Element('AssetPackage', Name=f'{pkg}', Version='0.1.0')
        ItemSettings = SubElement(AssetPackage, 'ItemSettings')
        ContentType = SubElement(ItemSettings, 'ContentType')
        ContentType.text = "SCENERY"
        Title = SubElement(ItemSettings, 'Title')
        Title.text = "Finland - Heightmaps for airports"
        Manufacturer = SubElement(ItemSettings, 'Manufacturer')
        Creator = SubElement(ItemSettings, 'Creator')
        Creator.text = 'morko'
        Flags = SubElement(AssetPackage, 'Flags')
        VisibleInStore = SubElement(Flags, 'Flags')
        VisibleInStore.text = 'false'
        CanBeReferenced = SubElement(Flags, 'CanBeReferenced')
        CanBeReferenced.text = 'false'
        AssetGroups = SubElement(AssetPackage, 'AssetGroups')
        Agroups = []
        Agroup = ElementTree.fromstring(
            '<AssetGroup Name="ContentInfo"><Type>ContentInfo</Type><Flags><FSXCompatibility>false</FSXCompatibility></Flags><AssetDir>PackageDefinitions\morko-dem-finland-heightmap-airports\ContentInfo</AssetDir><OutputDir>ContentInfo\morko-dem-finland-heightmap-airports</OutputDir></AssetGroup>')
        Agroup.set('Name', f'heightmap-finland-{pkg}')
        Agroup.find('Type').text = 'BGL'
        Agroup.find('AssetDir').text = f'heightmap{pkg}'
        Agroup.find('OutputDir').text = f'scenery\\heightmaps\\finland\\'
        Agroups.append(copy.deepcopy(Agroup))
        AssetGroups.extend(Agroups)
        outfile = open(
            f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\PackageDefinitions\{pkg}.xml', 'wb')
        outfile.write(ElementTree.tostring(
            AssetPackage, encoding='utf8', method='html'))
        outfile.close()
        genProjectXMLSingle(pkg)


def genProjectXMLSingle(qkey):
    Project = Element('Project', Version='2',
                      Name="Heightmap", FolderName=f"Packages")
    OutputDirectory = SubElement(Project, 'OutputDirectory')
    OutputDirectory.text = f'.'
    TemporaryOutputDirectory = SubElement(Project, 'TemporaryOutputDirectory')
    TemporaryOutputDirectory.text = f'_PackageInt'
    pkgfilelist = glob.glob(
        f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\PackageDefinitions\{qkey}.xml')
    Packages = []
    for pkg in pkgfilelist:
        pack = Element('Package')
        pack.text = os.path.relpath(
            pkg, r'C:\MyFSProjects\Heightmaps\morko-heightmap-nature')
        Packages.append(copy.deepcopy(pack))
    XMLPackages = SubElement(Project, 'Packages')
    XMLPackages.extend(Packages)
    outfile = open(
        f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\single{qkey}.xml', 'wb')
    outfile.write(ElementTree.tostring(
        Project, encoding='utf8', method='html'))
    outfile.close()


def genProjectXML(qkey):
    Project = Element('Project', Version='2',
                      Name="Heightmap", FolderName=f"Packages")
    OutputDirectory = SubElement(Project, 'OutputDirectory')
    OutputDirectory.text = f'.'
    TemporaryOutputDirectory = SubElement(Project, 'TemporaryOutputDirectory')
    TemporaryOutputDirectory.text = f'_PackageInt'
    pkgfilelist = glob.glob(
        f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\PackageDefinitions\morko-dem-finland-heightmap-airports.xml')
    Packages = []
    for pkg in pkgfilelist:
        pack = Element('Package')
        pack.text = os.path.relpath(
            pkg, r'C:\MyFSProjects\Heightmaps\morko-heightmap-nature')
        Packages.append(copy.deepcopy(pack))
    XMLPackages = SubElement(Project, 'Packages')
    XMLPackages.extend(Packages)
    outfile = open(
        f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\ProjHeightmap.xml', 'wb')
    outfile.write(ElementTree.tostring(
        Project, encoding='utf8', method='html'))
    outfile.close()


def runpkgtool(index, projfile):
    command = f'"C:\\MSFS SDK\Tools\\bin\\fspackagetool.exe" "{projfile}"'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    return [index, process.returncode]


def callback_runpkgtool(result):
    print(f'Index {result[0]} return {result[1]} ')


def callback_c(result):
    print(f'OK')


def runFSPackageTools():
    projlist = glob.glob(
        f'C:\MyFSProjects\Heightmaps\morko-heightmap-nature\ProjHeightmap.xml')
    #! Compiling level8 tile with 1024 heightmaps requires about 4 GB of ram
    #! Parallel accordingly
    pool = mp.Pool(int(6))
    for idx, proj in enumerate(projlist):
        pool.apply_async(runpkgtool, args=(
            idx, proj), callback=callback_runpkgtool)
    pool.close()
    # postpones the execution of next line of code until all processes in the queue are done.
    pool.join()


def qkeysfromshapefiles():
    totalcount = 0
    r = shapefile.Reader(r'C:\MyFSProjects\Heightmaps\EFRT_QKEY.shp')
    qKeys = []
    itr = 0
    split = []
    TopLevelQKeys = CoordsToQkeyList(latLongUL, latLongLR, Options)
    for shaperec in r.iterShapeRecords():
        tx, ty = LatLongToTileXY(LatLong(
            (shaperec.shape.bbox[1]+shaperec.shape.bbox[3])/2, (shaperec.shape.bbox[0]+shaperec.shape.bbox[2])/2), 13)
        qk = shaperec.record[0]
        qKeys.append([qk, shaperec.shape.bbox])
        itr += 1
    for TLQKey in TopLevelQKeys:
        subs = [x for x in qKeys if len(x) > 0 and x[0].startswith(TLQKey[0])]
        split.append(subs)
    threads = 16
    pool = mp.Pool(int(threads))
    for qkeys in enumerate(split):
        if len(qkeys[1]) > 0:
            # genTiles(qkeys[0],qkeys[1])
            pool.apply_async(genTiles, args=(
                qkeys[0], qkeys[1]), callback=callback_c)
    pool.close()
    # postpones the execution of next line of code until all processes in the queue are done.
    pool.join()
    genPackageDefinitionXML()


# # UpperLeft and LowerRight coordinates for target area (FInland)
latLongUL = LatLong(70.3, 18.5)
latLongLR = LatLong(59.5, 32.0)
# UpperLeft and LowerRight coordinates for target area
# latLongUL = LatLong(70.0920177,27.9596866)
# latLongLR = LatLong(70.0920177,27.9596866)

if __name__ == '__main__':
#    qkeysfromshapefiles()
    runFSPackageTools()
#    TopLevelQKeys = CoordsToQkeyList(latLongUL, latLongLR, Options)
#    generateCoverageSourceShapefile(ListAllSubQKeys(
#            TopLevelQKeys, Options.MaxLevel, Options.Basepath))
#     for tlQKey in TopLevelQKeys:
#         allSubQKeys = ListAllSubQKeys(
#             [tlQKey], Options.MaxLevel, Options.Basepath)
#         genTiles(allSubQKeys)
