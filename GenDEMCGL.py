from bingtile import ListAllSubQKeys, CoordsToQkeyList
from GMTiles import *
from pyramidGen import createPyramids
from cgl_generate import createCGLs
from packageGen import makePackageFolder
from misc import chunks
from dataclasses import dataclass
import os
import click
import cgl_generate as cglc


# Manifest data that will be written to the manifest.json in package folder.
# Fill title, creator, package_version and release notes.
manifest = {
    "dependencies": [],
    "content_type": "SCENERY",
    "title": "Scenery Title",
    "manufacturer": "",
    "creator": "creator",
    "package_version": "0.2.0",
    "minimum_game_version": "1.11.6",
    "release_notes": {
        "neutral": {
            "LastUpdate": "Latest release note \n With two rows",
            "OlderHistory": "These can be seen in package manager \n also this row"
        }
    }
}


@dataclass
# Options for configuring DEM tile and CGL generation
# CGLLevel: Bing maps tile level that will be the lowest resolution
#           in generated CGLs. Default 6. Don't change.
# MaxLevel: Highest Bing maps tile level used when generating tiles,
#           also DEM tile cutting level. Default 12. Don't change.
# Padding: If enabled (=1), generates extra tiles around target area
#          to minimize edge errors. Default 1.
# DEMInputFiles: List of source elevation data files, ELEVATION RELATIVE TO EGM2008
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
    CGLLevel: int = 6
    MaxLevel: int = 12
    padding: int = 1
    DEMInputFiles = [r'C:\test\und_egm2008_wgs84.bil', r'C:\karttadata\ALOS_egm2008\alos_egm2008.gmc',
                     r'C:\karttadata\korkeusmalli_egm2008\hila10m\10m_egm2008.gmc']
    GMExePath: str = r'C:\Program Files\GlobalMapper21.1_64bit\global_mapper.exe'
    GMThreads: int = mp.cpu_count()
    ProcessingThreads: int = mp.cpu_count()
    Basepath: str = os.path.abspath('./_temp/')
    TargetName: str = "morko-dem-finland-20m"


@dataclass
class LongLat():
    longitude: float = 0
    latitude: float = 0


# UpperLeft and LowerRight coordinates for target area
# If area covers multiple cgls, multiple cgls will be generated.
longlatUL = LongLat(20.857498, 69.043337)
longlatLR = LongLat(20.857498, 69.043337)



if __name__ == '__main__':
    TopLevelQKeys = CoordsToQkeyList(longlatUL, longlatLR, Options)
    createCoveragePolyShapefile(TopLevelQKeys, Options.Basepath)
    createGMVisualizationScript(Options)
    diskspaceneeded = calculateMaxDiskUsageMB(len(TopLevelQKeys), Options)
    print("Maximum space needed will be around " +
          str(int(diskspaceneeded)) + " MB")
    print("If padding tiles are not \"full\", it will be less")
    print("Showing quadkeys over source data in global mapper")
    print("When padding enabled, outermost tiles don't have to be completely covered")
    print("1/3 of width/height should be enough")
    print("Check if coverage is OK")
    visualize(Options.GMExePath, Options.Basepath)
    if click.confirm('Everything OK? Continue?', default=True):
        allSubQKeys = ListAllSubQKeys(
            TopLevelQKeys, Options.MaxLevel, Options.Basepath)
        totalSubCount = len(allSubQKeys)
        subsPerChunk = int(totalSubCount/Options.GMThreads)
        subQKeyChunks = chunks(allSubQKeys, subsPerChunk)
        for index, chunk in enumerate(subQKeyChunks):
            CreateGlobalMapperScript(index, chunk, Options)
        RunGMScripts(Options.GMExePath, Options.Basepath, Options.GMThreads)
        createPyramids(TopLevelQKeys, Options)
        createCGLs(TopLevelQKeys, Options.Basepath, Options.ProcessingThreads)
        makePackageFolder(TopLevelQKeys, Options, manifest)
        print("Done!")
        print("Ready to fly folder " + Options.TargetName + " is at")
        print(Options.Basepath)
        print("Just copy to Community to check if it works")
