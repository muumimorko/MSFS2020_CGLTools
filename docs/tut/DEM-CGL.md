# DEM CGL generation
Two main steps:
1. Translate source data elevation to EGM2008
2. Configure and run script "GenDEMCGL.py"

# 1. Translating elevation data to EGM2008
This step is necessary, because it is believed that the game uses elevation values relative to EGM2008 for the dem data. If translation is not done, absolute elevation values will be possibly tens of meters off.

This assumes you elevation data is in datum that uses wgs84 ellipsoid (for example epsg:4326).



## Step 1 Loading undulations.
Download egm08_25.gtx from http://download.osgeo.org/proj/vdatum/egm08_25/ 

and place it to 

```C:\OSGeo4W64\share\proj\```

![egm08gtx](/docs/tut/img/12_egm08gtx.png "egm08gtx")

Edit ``elev_wgs84_egm2008.py``

![evelUndSettings](/docs/tut/img/13_elevUnd.png "elevUndSettings")
On line 5 ```srcpath``` with path to your source files.

On line 6 ```dstpath``` to destination folder.

On line 7 ```epsg``` code of your source data, there will be no horizontal datum change, only elevations will be adjusted

Copy ``elev_wgs84_egm2008.py`` to ``C:\OSGeo4W64\``

Run ``OSGeo4W.bat`` from that folder.
It will open a terminal window.
In that terminal, run

```
py3_env
python3 elev_wgs84_egm2008.py
```

![UndDone](/docs/tut/img/14_UndDone.png "UndDone")

In ```dstpath``` there should be "undulated" files.

If you have multiple layers, do this from all of them.
# 2. Configure and run script "GenDEMCGL.py"

## Step 0 Importing source data to Global Mapper
Best way to manage large number of raster files in Global Mapper is to create a Map Catalog of them.

![Map Catalog Open](/docs/tut/img/1_MapCatalog.png "Map Catalog Open")
Click Create New Map Catalog.

![Map Catalog Save](/docs/tut/img/2_MapCatalogSave.png "Map Catalog Save")
Save the catalog to same folder with source data.

![Map Catalog Modify](/docs/tut/img/3_MapCatalogModify.png "Map Catalog Modify")
In this view you can add add files to the catalog, or a folder, using buttons "Add Files" or "Add Directory". Click Add Directory.

![Map Catalog Add](/docs/tut/img/4_AddFolder.png "Map Catalog Add")
Select folder that contains source files.

![Map Catalog Filter](/docs/tut/img/5_Filter.png "Map Catalog Filter")
In this screen you could filter the files by file extension or partial name for example. Keep recurse on if the files are in subfolders.

![Map Catalog Success](/docs/tut/img/6_Added.png "Map Catalog Success")
Successfully added file(s) show in the Modify Map Catalog Window.

![Map Added](/docs/tut/img/7_Loaded.png "Map Added")
Loaded map can be seen in the main window.

If you have multiple layers, do this from all of them.

## Step 1
Open and edit ```GenDEMCGL.py```
- Fill manifest data (title, creator, package_version)
![Manifest](/docs/tut/img/15_Manifest.png "Manifest")

- Edit Options
  - DEM input files is a list of source data, that is corrected to EGM2008, all specified files will be loaded to Global Mapper. First item in the list will be at the bottom, and last item at the top. So input order should be from lowest quality to highest quality.

-Get UL and LR

![Projection](/docs/tut/img/10_Projection.png "Projection")
Load All your source layers in Global Mapper and change projection to Geographic WGS84.

![ULLR](/docs/tut/img/16_Coordinates.png "ULLR")
Note the UL and LR coordinates by hovering mouse over the point and writing down coordinates on the bottom of the window.


- Run the script

First ouput will be like:
```
Maximum space needed will be around 63037 MB
If padding tiles are not "full", it will be less
Showing quadkeys over source data in global mapper
When padding enabled, outermost tiles don't have to be completely covered
1/3 of width/height should be enough
Check if coverage is OK
```
On the first row it tells the estimated maximum disk space need for the project.
Then an instance of Global Mapper will open and show an estimate like this:
![Estimate](/docs/tut/img/17_Estimate.png "Estimate")
As padding is enabled, outermost tiles will not be built. So actual covered area will be area in this red rectangle:
![Area](/docs/tut/img/18_Area.png "Area")

As the coverage looks OK, we close Global Mapper and answer "y" to the question asked:
```
Everything OK? Continue? [Y/n]:y
```
Processing will then begin and there will be output to the console. This will take a considerable amount of time on large areas. This example project of 18 CGLs (and 22 padding tiles) took 50 minutes to build on a Ryzen 1700, 16gb of ram and nvme ssd.

Finally you should see:

```
Ready to fly folder morko-dem-finland-lvl12 is at
C:\Users\teemu\source\repos\MSFS2020_CGLTools\_temp
Just copy to Community to check if it works
```

And that's about that :)