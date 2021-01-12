# MSFS CGL Tools
Tools for creating terrain stuff for MSFS 2020

Code might bite your nose off if even if you don't look at it the wrong way and "docs" might melt your brain, sorry about that.

## Prereg software
```
Python3
OSGeo4W
Blue Marble Global Mapper (other mapping packages can be adapted)

```
## Python modules
```
numpy
matplotlib
opencv-python
pyshp
click
```

## DEM CGL generation in nutshell
- Install prereg software and python modules
- Convert source data elevation to EGM2008
- edit "GenDEMCGL.py" and configure manifest, settings, and coordinates
- run "GenDEMCGL.py", preferably in debugger (Visual Studio Code), so you can set breakpoints to Raised exceptions.

## [More Detailed How-To](docs/tut/DEM-CGL.md)

## Credits
- Szpike on the FSDeveloper Forum for:
  - CGL index delta decompression details
  - CGL content type, and other CGL header values

## Considerations
- Currently generation is possible to level 12 (~40 meter resolution on the equator, more at higher latitudes).
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
- [ ] Blending to in-game DEM
- [ ] Vector file type format
- [ ] Vector generation
- [ ] Anything and everything else


