#!/bin/bash

# Run the Docker container
docker run --rm --network="host" -v "$PWD:/srv/jekyll" -p 4000:4000 --entrypoint /bin/bash -it my-jekyll-site
