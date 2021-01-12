import glob
from osgeo import gdal
import os
import multiprocessing as mp
srcpathwildcard=r'I:\karttadata\korkeusmalli\250m\*.tif'
dstpath=r'I:\egm2008\korkeusmalli\250m\\'
files = glob.glob(srcpathwildcard)
count=len(files)
counter=0

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def compressChunk(index,fileschunk):
    for file in fileschunk:
        filename=os.path.basename(file)
        dpath=dstpath+filename
        kwargs = {'multithread':True,'format': 'GTiff',  'geoloc': False,'srcSRS':"+init=EPSG:3067 +geoidgrids=C:\OSGeo4W64\share\proj\egm08_25.gtx",'dstSRS':"EPSG:3067"}
        os.makedirs(os.path.dirname(dpath), exist_ok=True)
        ds = gdal.Warp(dpath,file, **kwargs)
        del ds
    return index


def collect_result(result):
    print(result)


def convertMT(filesall):
    srcfilechunks = chunks(filesall, 256)
    pool = mp.Pool(int(2))
    for idx, chunk in enumerate(srcfilechunks):
        pool.apply_async(compressChunk, args=(
            idx, chunk), callback=collect_result)
    pool.close()
    # postpones the execution of next line of code until all processes in the queue are done.
    pool.join()

if __name__ == '__main__':
    convertMT(files)