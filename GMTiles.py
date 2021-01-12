
from bingtile import *
import shapefile
import subprocess
import os
import glob
import multiprocessing as mp
import time
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


def RunGMScripts(exepath,basepath,threads):
    files = glob.glob(basepath+r'\tilescript*.gms')
    pool = mp.Pool(threads)
    res=[]
    for idx,script in enumerate(files):
        res.append('')
        res[idx]=pool.apply_async(runGMScript, args=(script,exepath),callback=None)
    pool.close()
    donecount=0
    while True:
        time.sleep(1)
        dc=0
        for re in res:
            if re.ready():
                dc+=1
        if dc != donecount:
            print(f'Done {dc} of {len(res)}')
            donecount=dc       
        if dc==len(res):
            break
    pool.join()
    
def runGMScript(file,exepath):
    subprocess.run(exepath +" "+ file)
    return 0


def createGMVisualizationScript(options):
    script = open(options.Basepath+"/visualize.gmw", 'w')
    script.write('GLOBAL_MAPPER_SCRIPT VERSION=1.00\n')
    for path in options.DEMInputFiles:
        script.write('IMPORT FILENAME=\"'+path +
                     '" ELEV_UNITS=METERS ELEV_SCALE=1\n')
    script.write('IMPORT FILENAME=\"'+options.Basepath +
                 '\\qKeyCoverage.shp" LABEL_FIELD="name" PROJ="EPSG:4326"\n')


def visualize(exepath, basepath):
    process = subprocess.Popen(
        "\""+exepath + "\" " + basepath+'\\visualize.gmw', shell=True, stdout=subprocess.PIPE)
    process.wait()
    
def createCoveragePolyShapefile(qKeys, basepath):
    w = shapefile.Writer(basepath+r'\qKeyCoverage.shp')
    w.field('name', 'C')
    w.field('paddingtile', 'L')
    for qKey in qKeys:
        west, north, east, south = qKeyToBoundingLatLong(qKey[0])
        w.poly([[[west, north], [east, north], [east, south], [west, south]]])
        w.record(qKey[0], qKey[1])
    w.close()


def calculateMaxDiskUsageMB(qKeyCount, options):
    singleQKeyTiles = SubtileCount(
        options.CGLLevel, options.CGLLevel, options.MaxLevel)
    singleQKeyDeltas = SubtileCount(
        options.CGLLevel, options.CGLLevel+1, options.MaxLevel)
    totalFileCount = qKeyCount*singleQKeyTiles+qKeyCount*singleQKeyTiles
    totalSize = totalFileCount*132098/1048576+(qKeyCount*2*100)
    return totalSize