import multiprocessing as mp
import os
import glob
import struct
import lzma
import math
import binascii

""" CGL building """


def custom_key(str):
    return len(str), str.lower()


def createLayout(tiles):
    """Creates layout byte data
    Args:
        tiles (list): List of tile filenames.
    Returns:
        bytearray: Bytearray of delta subtile positions.
    """
    bts = bytearray()
    levelchangevalue = 4096
    prevval = 0
    pervlevel = 0
    for tile in tiles:
        subkey = tile[str(tile).index("_")+1+6:str(tile).index(".rw")]
        subval = 0
        level = len(subkey)
        if subkey == '':
            subval = 0
        else:
            subval = int(subkey, 4)
        delta = 0
        if level == pervlevel:
            delta = subval-prevval
            prevval = prevval+delta
        else:
            delta = levelchangevalue-prevval+subval
            prevval = 0
        pervlevel = level
        valbts = delta.to_bytes(2, "little")
        bts.append(valbts[0])
        bts.append(valbts[1])
    return bts


def createBlob(tiles):
    """ Compressed all tiles to single binary blob.
    Args:
        tiles (list): List of tile names
    Returns:
        blob: Bytearray blob.
        compressedsizes: Sizes of compressed tiles in blob.
    """
    blob = bytearray()
    counter = 0
    compressedsizes = []
    uncompressedsizes = []
    prop = 93
    pb = math.floor(prop / (9 * 5))
    prop = prop-(pb * 9 * 5)
    lp = math.floor(prop / 9)
    lc = math.floor(prop - lp * 9)
    my_filters = [{"id": lzma.FILTER_LZMA1,
                   "preset": lzma.PRESET_DEFAULT, "lc": lc, "lp": lp, "pb": pb, "dict_size": 65536}, ]
    for tile in tiles:
        qkey = tile[str(tile).index("_")+1:str(tile).index(".rw")]
        infile = open(tile, 'rb')
        inarr = infile.read()
        infile.close()
        uncompressedsizes.append(len(inarr))
        compressed = lzma.compress(
            inarr, lzma.FORMAT_RAW, -1, None, my_filters)
        print(str(counter))
        counter += 1
        compressedsizes.append(len(compressed))
        blob += bytearray(compressed)
    return blob, compressedsizes, uncompressedsizes


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def compressChunk(chunkid, chunk):
    blob = bytearray()
    compressedsizes = []
    uncompressedsizes = []
    prop = 93
    pb = math.floor(prop / (9 * 5))
    prop = prop-(pb * 9 * 5)
    lp = math.floor(prop / 9)
    lc = math.floor(prop - lp * 9)
    my_filters = [{"id": lzma.FILTER_LZMA1,
                   "preset": lzma.PRESET_DEFAULT, "lc": lc, "lp": lp, "pb": pb, "dict_size": 65536}, ]
    for tile in chunk:
        qkey = tile[str(tile).index("_")+1:str(tile).index(".rw")]
        infile = open(tile, 'rb')
        inarr = infile.read()
        infile.close()
        uncompressedsizes.append(len(inarr))
        compressed = lzma.compress(
            inarr, lzma.FORMAT_RAW, -1, None, my_filters)
        compressedsizes.append(len(compressed))
        blob += bytearray(compressed)
    return [chunkid, (blob, compressedsizes, uncompressedsizes)]


compressedreturns = {}
# Step 2: Define callback function to collect the output in `results`


def collect_result(result):
    global compressedreturns
    compressedreturns[result[0]] = result[1]


def createBlobMT(tiles):
    """ Compressed all tiles to single binary blob.
    Args:
        tiles (list): List of tile names
    Returns:
        blob: Bytearray blob.
        compressedsizes: Sizes of compressed tiles in blob.
    """
    srctilechunks = chunks(tiles, 256)
    blob = bytearray()
    counter = 0
    compressedsizes = []
    uncompressedsizes = []
    pool = mp.Pool(int(mp.cpu_count()))
    for idx, chunk in enumerate(srctilechunks):
        pool.apply_async(compressChunk, args=(
            idx, chunk), callback=collect_result)
    pool.close()
    # postpones the execution of next line of code until all processes in the queue are done.
    pool.join()
    itr = 0
    while itr < len(compressedreturns):
        blob += compressedreturns[itr][0]
        compressedsizes += compressedreturns[itr][1]
        uncompressedsizes += compressedreturns[itr][2]
        itr += 1
    return blob, compressedsizes, uncompressedsizes


def deltaSizes(sizes):
    deltacompressedsizes = bytes()
    previoussize = 0
    for idx, size in enumerate(sizes):
        delta = size-previoussize
        print("Prev: " + f'{previoussize:08}')
        print("Curr: " + f'{size:08}')
        print("Delta: " + f'{delta:08}')
        previoussize = size
        if idx == 0:
            firstword = 32768
            while delta > 65400:
                delta = delta - 65536
                firstword += 1
            deltacompressedsizes = deltacompressedsizes + \
                firstword.to_bytes(2, 'little')
            deltacompressedsizes = deltacompressedsizes + \
                delta.to_bytes(2, 'little')
        elif delta > 65441:
            delta = delta-65536
            print("Delta: " + f'{delta:08}')
            deltacompressedsizes = deltacompressedsizes + \
                binascii.unhexlify("0180")
            deltacompressedsizes = deltacompressedsizes + \
                delta.to_bytes(2, 'little')
        elif delta > 16384:
            deltacompressedsizes = deltacompressedsizes + \
                binascii.unhexlify("0080")
            deltacompressedsizes = deltacompressedsizes + \
                delta.to_bytes(2, 'little')
        elif delta < 0:
            firstword = 65536
            while delta < 0:
                firstword -= 1
                delta = 65536-delta*(-1)
            print("Delta: " + f'{delta:08}')
            deltacompressedsizes = deltacompressedsizes + \
                firstword.to_bytes(2, 'little')
            deltacompressedsizes = deltacompressedsizes + \
                delta.to_bytes(2, 'little')
        else:
            deltacompressedsizes = deltacompressedsizes + \
                delta.to_bytes(2, 'little')
    return deltacompressedsizes


def deltasToUncompressed(compressedsizes, uncompressedsizes):
    deltastouncompressed = bytes()
    for csize, usize in zip(compressedsizes, uncompressedsizes):
        # TODO Uncompressed size is not constant, provide input list
        delta = usize-csize
        firstbyte = 32768
        while delta > 65535:
            delta = delta-65536
            firstbyte += 1
        print("fb:"+f'{firstbyte:06}'+"delta:"+f'{delta:06}')
        deltastouncompressed = deltastouncompressed + \
            firstbyte.to_bytes(2, 'little')
        deltastouncompressed = deltastouncompressed+delta.to_bytes(2, 'little')
    return deltastouncompressed


def createUncompressedHeader(btalayout, deltasizes, dtous):
    header = bytearray()
    for byte in btalayout:
        header.append(byte)
    for byte in deltasizes:
        header.append(byte)
    for byte in dtous:
        header.append(byte)
    return header


def createCompressedHeader(header):
    prop = 93
    pb = math.floor(prop / (9 * 5))
    prop = prop-(pb * 9 * 5)
    lp = math.floor(prop / 9)
    lc = math.floor(prop - lp * 9)
    my_filters = [{"id": lzma.FILTER_LZMA1,
                   "preset": lzma.PRESET_DEFAULT, "lc": lc, "lp": lp, "pb": pb, "dict_size": 65536}, ]
    compressed = lzma.compress(
        header, lzma.FORMAT_RAW, -1, None, my_filters)[0:]
    headerc = bytearray()
    for byte in compressed:
        headerc.append(byte)
    return headerc


def compileCGL(headerc, blob, tilecount):
    cgl = bytearray()
    headerlen = len(headerc)
    cglheader = binascii.unhexlify(
        "4642734118000000000000000000000003000200010000003100000002000000")
    cglheader = cglheader + \
        tilecount.to_bytes(4, 'little')+binascii.unhexlify("34000000")
    cglheader = cglheader + \
        headerlen.to_bytes(3, 'little') + \
        binascii.unhexlify("80000001005D5D0000")
    for byte in cglheader:
        cgl.append(byte)
    for byte in headerc:
        cgl.append(byte)
    for byte in blob:
        cgl.append(byte)
    return cgl


def createCGL(srcpaths, dstpath):
    tiles = srcpaths
    tiles = sorted(tiles, key=custom_key)
    tilecount = len(tiles)
    btalayout = createLayout(tiles)
    if os.path.dirname(dstpath) != '':
        if not os.path.exists(os.path.dirname(dstpath)):
            os.makedirs(os.path.dirname(dstpath))
    btablob, compressedsizes, uncompressedsizes = createBlobMT(tiles)
    deltasizes = deltaSizes(compressedsizes)
    dtous = deltasToUncompressed(compressedsizes, uncompressedsizes)
    uncompressedheader = createUncompressedHeader(btalayout, deltasizes, dtous)
    compressedheader = createCompressedHeader(uncompressedheader)
    cgl = compileCGL(compressedheader, btablob, tilecount)
    outfile = open(dstpath, 'wb', buffering=1048576)
    outfile.write(cgl)
    outfile.close()
