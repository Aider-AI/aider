#!/bin/bash

# Run the Docker container
docker run \
       --rm \
       -v "$PWD/website:/site" \
       -p 4000:4000 \
       -e HISTFILE=/site/.bash_history \
       --entrypoint /bin/bash \
       -it \
       my-jekyll-site

