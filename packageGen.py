import os
import cv2
import json
import numpy as np
from datetime import datetime
from calendar import timegm
import time
from shutil import copyfile
def dt_to_filetime(dt):
    EPOCH_AS_FILETIME = 116444736000000000  # January 1, 1970 as MS file time
    HUNDREDS_OF_NANOSECONDS = 10000000
    return EPOCH_AS_FILETIME + (timegm(dt.timetuple()) * HUNDREDS_OF_NANOSECONDS)

from shutil import rmtree
def makePackageFolder(TopLevelQKeys, options, manifest):
    foldername = options.Basepath+"\\"+options.TargetName+"\\"
    if os.path.isdir(foldername):
        rmtree(foldername,ignore_errors=True)
    os.makedirs(os.path.dirname(foldername), exist_ok=True)
    manifestfile = open(foldername+"manifest.json", 'w')
    manifestfile.write(json.dumps(manifest, indent=4))
    manifestfile.close()
    thumbnail = np.zeros((170, 412, 3), dtype='uint8')
    font = cv2.FONT_HERSHEY_COMPLEX
    cv2.putText(thumbnail, options.TargetName, (10, 95),
                font, 1, (255, 255, 255), 2, cv2.LINE_AA)
    os.makedirs(os.path.dirname(foldername+"ContentInfo\\" +
                                options.TargetName+"\\"), exist_ok=True)
    cv2.imwrite(foldername+"ContentInfo\\" +
                options.TargetName+"\\Thumbnail.jpg", thumbnail)
    layout = {
        "content": [
            {
                "path": "ContentInfo/"+options.TargetName+"/Thumbnail.jpg",
                "size": os.path.getsize(foldername+"ContentInfo\\"+options.TargetName+"\\Thumbnail.jpg"),
                "date": dt_to_filetime(datetime.fromtimestamp(time.time()))
            }
        ]
    }
    for qKey in TopLevelQKeys:
        if qKey[1] == False:
            os.makedirs(os.path.dirname(
                foldername+"CGL\\"+qKey[0][0:3]+"\\"), exist_ok=True)
            copyfile(options.Basepath+"\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6] +
                     ".cgl", foldername+"CGL\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6]+".cgl")
            size = os.path.getsize(
                foldername+"CGL\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6]+".cgl")
            path = os.path.relpath(
                foldername+"CGL\\"+qKey[0][0:3]+"\\dem"+qKey[0][3:6]+".cgl", foldername).replace("\\", "/")
            date = dt_to_filetime(datetime.fromtimestamp(time.time()))
            layout["content"].append(
                {"path": path, "size": size, "date": date})
    layoutfile = open(foldername+"layout.json", 'w')
    layoutfile.write(json.dumps(layout, indent=4))
    layoutfile.close()