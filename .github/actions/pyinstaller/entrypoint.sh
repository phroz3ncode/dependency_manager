#!/bin/bash

# Fail on errors.
set -e

# Make sure .bashrc is sourced
. /root/.bashrc

python -m pip install --upgrade pip wheel setuptools

ls .
cd src
pip install -r requirements.txt
pyinstaller --clean -y --dist ./dist/windows ./dependency_manager.spec

chown -R --reference=. ./dist/windows