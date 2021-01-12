import os
import glob
import cgl_generate as cglc
import bingtile

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
    idx=(-1)*padleft
    idy+=1
    
for qkey in qkeystoprocess:
    files = glob.glob("Tile/6/dem_"+qkey+"*.bil")
    files +=glob.glob("Delta/7/dem_"+qkey+"*.bil")
    files +=glob.glob("Delta/8/dem_"+qkey+"*.bil")
    files +=glob.glob("Delta/9/dem_"+qkey+"*.bil")
    files +=glob.glob("Delta/10/dem_"+qkey+"*.bil")
    files +=glob.glob("Delta/11/dem_"+qkey+"*.bil")
    files +=glob.glob("Delta/12/dem_"+qkey+"*.bil")
    if __name__ == '__main__':
        cglc.createCGL(files,qkey[0:3]+"/dem"+qkey[3:6]+".cgl")