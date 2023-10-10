#!/bin/bash

# Fail on errors.
set -e

# Make sure .bashrc is sourced
. /root/.bashrc

# Allow the workdir to be set using an env var.
# Useful for CI pipiles which use docker for their build steps
# and don't allow that much flexibility to mount volumes
SRCDIR=$1

WORKDIR=${SRCDIR:-/src}

python -m pip install --upgrade pip wheel setuptools

cd $WORKDIR
pip install -r requirements.txt
pyinstaller --clean -y --dist ./dist/windows --onefile --name $(var_version) \
  --add-data "depmanager/resources/morph.jpg;." \
  --add-data "depmanager/resources/plugin.jpg;." \
  --add-data "depmanager/resources/sound.jpg;." \
  --add-data "depmanager/resources/unity.jpg;." \
  depmanager/run_var.py

chown -R --reference=. ./dist/windows