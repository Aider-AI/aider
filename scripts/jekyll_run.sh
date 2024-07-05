#!/bin/bash

# Run the Docker container
docker run \
       --rm \
       -v "$PWD/aider/website:/site" \
       -p 4000:4000 \
       -e HISTFILE=/site/.bash_history \
       -it \
       my-jekyll-site

#       --entrypoint /bin/bash \

