#!/bin/bash

set -euo pipefail

cd ~/Pictures/Snapshots

echo --------------------------
echo Generating tags [Uploading] at `date`
echo --------------------------
python ~/.local/bin/flickrsmartsync/flickrsmartsync --generate-tags
echo --------------------------
echo Downloading at `date`
echo --------------------------
python ~/.local/bin/flickrsmartsync/flickrsmartsync --download 2018
echo --------------------------
echo Finished at `date`
echo --------------------------

