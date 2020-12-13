# %%
import cgl_decompress as cgld
import cgl_generate as cglc
import glob

# decompresses a cgl, only for DEMs
# generates also header files so resulting .rw (BIL) files can be loaded in Global Mapper
cgld.decompress("_testfiles/dem102231.cgl", "102231", "_testfiles/dem120231/")
# %%
