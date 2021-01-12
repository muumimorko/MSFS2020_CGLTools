import statistics
import time
import glob
import os

# Run scripts generated in previous file
files = glob.glob("tilescript*.gms")

for file in files:
    os.system(file)

# Monitor tile creation process
tilecount = 4096
deltas = []
previous = 0
while True:
    count = len(glob.glob("Tile/*/*.rw"))
    if previous == 0:
        previous = count
    else:
        delta = count-previous
        deltas.append(delta)
        if len(deltas) > 30:
            deltas.pop(0)
        avg = statistics.mean(deltas)
        left = tilecount-count
        previous=count
        if avg > 0:
            secondsleft = left/avg
        else:
            secondsleft = -1
        print("Done: " + str(count).rjust(7, '0')+" of " +
              str(tilecount) + " Time left: " + f"{secondsleft:.0f}")
        time.sleep(1)
        if count == tilecount:
            break
