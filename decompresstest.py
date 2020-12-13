# %%
import cgl_decompress as cgld
import cgl_generate as cglc
import glob

# decompresses a cgl, only for DEMs
# generates also header files so resulting .rw (BIL) files can be loaded in Global Mapper
cgld.decompress("_testfiles/dem223.cgl", "120223", "_testfiles/dem120223/")
# %%
