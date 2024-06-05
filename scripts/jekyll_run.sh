#!/bin/bash

# Run the Docker container
docker run \
       --rm \
       -v "$PWD:/site" \
       -p 4000:4000 \
       my-jekyll-site

#       -e HISTFILE=/srv/jekyll/.bash_history \
#       --entrypoint /bin/bash \
#       -it \
