#!/usr/bin/env bash
# Sample bash script used as a repomap fixture.

# POSIX-style function definition
greet() {
    local name="${1:-World}"
    echo "Hello, ${name}!"
}

# Keyword-style function definition
function deploy() {
    local env="${1:-production}"
    echo "Deploying to ${env}..."
}

# Another helper
function cleanup() {
    echo "Cleaning up..."
    rm -f /tmp/deploy_lock
}

# Main entry point
main() {
    greet "$@"
    deploy
    cleanup
}

main "$@"
