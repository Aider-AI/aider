#!/bin/bash

# exit when any command fails
set -e

# only do this if the files don't exist ai!
ln -s /npm-install/node_modules /npm-install/package-lock.json .


sed -i 's/\bxtest(/test(/g' *.spec.js
npm run test

