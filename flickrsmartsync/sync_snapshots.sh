#!/bin/bash
# cd ~/Pictures/Snapshots
echo --------------------------
echo Spawning at `date`
echo Starting at `date` ; \
python ~/Applications/flickrsmartsync/flickrsmartsync --generate-tags ; \
python ~/Applications/flickrsmartsync/flickrsmartsync --download . ; \
echo Finished at `date` ; \
