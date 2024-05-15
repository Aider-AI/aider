#!/bin/bash

# Run the Docker container
docker run --rm -v "$PWD:/srv/jekyll" -p 4000:4000 -it my-jekyll-site
