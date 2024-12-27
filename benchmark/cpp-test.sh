#!/bin/bash

# exit when any command fails
set -e

[ ! -d "build" ] && mkdir build
cd build
cmake -G "Unix Makefiles" ..
make


