#!/bin/bash

# exit when any command fails
set -e

# Create symlinks if they don't exist
[ ! -e node_modules ] && ln -s /npm-install/node_modules .
[ ! -e package-lock.json ] && ln -s /npm-install/package-lock.json .


sed -i 's/\bxtest(/test(/g' *.spec.js
npm run test

