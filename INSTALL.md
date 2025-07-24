# Install

```bash
# Clone the aider repo
git clone https://github.com/Aider-AI/aider.git aider-polyglot

# Create the scratch dir to hold benchmarking results inside the main aider dir:
cd aider-polyglot
mkdir benchmarks

# Clone the repo with the exercises
git clone https://github.com/Aider-AI/polyglot-benchmark benchmarks/polyglot-benchmark

# Build the docker container
./benchmark/docker_build.sh
```

For more info, check `benchmark/README.md`