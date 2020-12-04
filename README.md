# MSFS CGL Tools
Tools for creating terrain stuff for MSFS 2020

Code might bite your nose off if even if you don't look at it the wrong way and "docs" might melt your brain, sorry about that.

## Prereg
```
Python (tested on 3.8)
numpy==1.19.3
matplotlib
opencv-python
Blue Marble Global Mapper (other mapping packages can be adapted)
```

## DEM CGL generation
Install prereg, configure and run each numbered script. Just beware of wild hardcoded pathnames and other "variables" :D

Then study package folder structure shown as "creator-exampledem" folder, copy generated cgls to right paths, fill layout.json (sizes and dates don't matter, only paths), manifest.json and maybe change thumbnail. Copy to Community folder and hope for the best.

## Considerations
- Currently generation is possible to level 12 (~20 meter resolution).
- Will replace whole level 6 tile -> minimum coverage ~600\*600 Km.

## Progress
- [X] High level structure of CGL files
- [X] Decompression with fixed parameters
- [ ] Near complete understanding of possible values and data types 
- [ ] Decompression of all CGLs
- [X] Re-compressing decompressed CGLs with fixed parameters
- [ ] Re-compressing of all CGLs
- [X] DEM creation from source data
- [X] Successfull loading of self-generated DEM CGL.
- [ ] Blending to in-game DEM?
- [ ] Vector file type format
- [ ] Vector generation
- [ ] Anything and everything else


