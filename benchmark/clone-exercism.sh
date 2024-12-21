#!/bin/bash

# Create directories if they don't exist
mkdir -p tmp.benchmarks/exercism

# Change to the exercism directory
cd tmp.benchmarks/exercism

# List of languages to clone
languages=("cpp" "go" "java" "javascript" "python" "rust")

# Clone each repository
for lang in "${languages[@]}"; do
    if [ ! -d "$lang" ]; then
        echo "Cloning $lang repository..."
        git clone "https://github.com/exercism/$lang"
    else
        echo "$lang repository already exists"
    fi
done
