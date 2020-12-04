# Functions to translate between LatLong/XY/Quadkey coordinate systems
# Adapted from https://docs.microsoft.com/en-us/bingmaps/articles/bing-maps-tile-system
##------------------------------------------------------------------------------  
## <copyright company="Microsoft">  
##     Copyright (c) 2006-2009 Microsoft Corporation.  All rights reserved.  
## </copyright>  
##------------------------------------------------------------------------------  
  
import math

EarthRadius = 6378137
MinLatitude = -85.05112878
MaxLatitude = 85.05112878
MinLongitude = -180
MaxLongitude = 180

# <summary>
# Clips a number to the specified minimum and maximum values.
# </summary>
# <param name="n">The number to clip.</param>
# <param name="minValue">Minimum allowable value.</param>
# <param name="maxValue">Maximum allowable value.</param>
# <returns>The clipped value.</returns>
def Clip(n, minValue, maxValue):
    return min(max(n, minValue), maxValue)

# <summary>
# Determines the map width and height (in pixels) at a specified level
# of detail.
# </summary>
# <param name="levelOfDetail">Level of detail, from 1 (lowest detail)
# to 23 (highest detail).</param>
# <returns>The map width and height in pixels.</returns>
def MapSize(levelOfDetail):
    return 256 << levelOfDetail


# <summary>
# Determines the ground resolution (in meters per pixel) at a specified
# latitude and level of detail.
# </summary>
# <param name="latitude">Latitude (in degrees) at which to measure the
# ground resolution.</param>
# <param name="levelOfDetail">Level of detail, from 1 (lowest detail)
# to 23 (highest detail).</param>
# <returns>The ground resolution, in meters per pixel.</returns>
def GroundResolution(latitude, levelOfDetail):
    latitude = Clip(latitude, MinLatitude, MaxLatitude)
    return math.cos(latitude * math.pi / 180) * 2 * math.pi * EarthRadius / MapSize(levelOfDetail)

# <summary>
# Determines the map scale at a specified latitude, level of detail,
# and screen resolution.
# </summary>
# <param name="latitude">Latitude (in degrees) at which to measure the
# map scale.</param>
# <param name="levelOfDetail">Level of detail, from 1 (lowest detail)
# to 23 (highest detail).</param>
# <param name="screenDpi">Resolution of the screen, in dots per inch.</param>
# <returns>The map scale, expressed as the denominator N of the ratio 1 : N.</returns>
def MapScale(latitude, levelOfDetail, screenDpi):
    return GroundResolution(latitude, levelOfDetail) * screenDpi / 0.0254

# <summary>
# Converts a point from latitude/longitude WGS-84 coordinates (in degrees)
# into pixel XY coordinates at a specified level of detail.
# </summary>
# <param name="latitude">Latitude of the point, in degrees.</param>
# <param name="longitude">Longitude of the point, in degrees.</param>
# <param name="levelOfDetail">Level of detail, from 1 (lowest detail)
# to 23 (highest detail).</param>
# <param name="pixelX">Output parameter receiving the X coordinate in pixels.</param>
# <param name="pixelY">Output parameter receiving the Y coordinate in pixels.</param>
def LatLongToPixelXY(latitude, longitude, levelOfDetail):
    latitude = Clip(latitude, MinLatitude, MaxLatitude)
    longitude = Clip(longitude, MinLongitude, MaxLongitude)
    x = (longitude + 180) / 360
    sinLatitude = math.sin(latitude * math.pi / 180)
    y = 0.5 - math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * math.pi)
    mapSize = MapSize(levelOfDetail)
    pixelX = round(Clip(x * mapSize + 0.5, 0, mapSize - 1))
    pixelY = round(Clip(y * mapSize + 0.5, 0, mapSize - 1))
    return pixelX, pixelY

# <summary>
# Converts a pixel from pixel XY coordinates at a specified level of detail
# into latitude/longitude WGS-84 coordinates (in degrees).
# </summary>
# <param name="pixelX">X coordinate of the point, in pixels.</param>
# <param name="pixelY">Y coordinates of the point, in pixels.</param>
# <param name="levelOfDetail">Level of detail, from 1 (lowest detail)
# to 23 (highest detail).</param>
# <param name="latitude">Output parameter receiving the latitude in degrees.</param>
# <param name="longitude">Output parameter receiving the longitude in degrees.</param>
def PixelXYToLatLong(pixelX, pixelY, levelOfDetail):
    mapSize = MapSize(levelOfDetail)
    x = (Clip(pixelX, 0, mapSize - 1) / mapSize) - 0.5
    y = 0.5 - (Clip(pixelY, 0, mapSize - 1) / mapSize)
    latitude = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
    longitude = 360 * x
    return latitude, longitude

# <summary>
# Converts pixel XY coordinates into tile XY coordinates of the tile containing
# the specified pixel.
# </summary>
# <param name="pixelX">Pixel X coordinate.</param>
# <param name="pixelY">Pixel Y coordinate.</param>
# <param name="tileX">Output parameter receiving the tile X coordinate.</param>
# <param name="tileY">Output parameter receiving the tile Y coordinate.</param>
def PixelXYToTileXY(pixelX, pixelY):
    tileX = math.floor(pixelX / 256)
    tileY = math.floor(pixelY / 256)
    return tileX, tileY

# <summary>
# Converts tile XY coordinates into pixel XY coordinates of the upper-left pixel
# of the specified tile.
# </summary>
# <param name="tileX">Tile X coordinate.</param>
# <param name="tileY">Tile Y coordinate.</param>
# <param name="pixelX">Output parameter receiving the pixel X coordinate.</param>
# <param name="pixelY">Output parameter receiving the pixel Y coordinate.</param>
def TileXYToPixelXY(tileX, tileY):
    pixelX = tileX * 256
    pixelY = tileY * 256
    return pixelX, pixelY


# <summary>
# Converts tile XY coordinates into a QuadKey at a specified level of detail.
# </summary>
# <param name="tileX">Tile X coordinate.</param>
# <param name="tileY">Tile Y coordinate.</param>
# <param name="levelOfDetail">Level of detail, from 1 (lowest detail)
# to 23 (highest detail).</param>
# <returns>A string containing the QuadKey.</returns>
def TileXYToQuadKey(tileX, tileY, levelOfDetail):
    quadKey = ''
    i = levelOfDetail
    while i > 0:
        digit = 0
        mask = 1 << (i - 1)
        if (tileX & mask) != 0:
            digit = digit+1
        if (tileY & mask) != 0:
            digit = digit+1
            digit = digit+1
        quadKey += str(digit)
        i = i-1
    return quadKey

# <summary>
# Converts a QuadKey into tile XY coordinates.
# </summary>
# <param name="quadKey">QuadKey of the tile.</param>
# <param name="tileX">Output parameter receiving the tile X coordinate.</param>
# <param name="tileY">Output parameter receiving the tile Y coordinate.</param>
# <param name="levelOfDetail">Output parameter receiving the level of detail.</param>
def QuadKeyToTileXY(quadKey):
    tileX = 0
    tileY = 0
    levelOfDetail = len(quadKey)
    i = levelOfDetail
    while i > 0:
        mask = 1 << (i - 1)
        if quadKey[levelOfDetail - i] == '0':
            deadplay = 0
        elif quadKey[levelOfDetail - i] == '1':
            tileX |= mask
        elif quadKey[levelOfDetail - i] == '2':
            tileY |= mask
        elif quadKey[levelOfDetail - i] == '3':
            tileX |= mask
            tileY |= mask
        else:
            print("Invalid QuadKey digit sequence.")
        i = i-1
    return tileX, tileY, levelOfDetail
