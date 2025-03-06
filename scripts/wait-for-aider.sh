#!/usr/bin/env bash

# usage: pycharm preferences > tools > file watchers > add
#
# - Files to watch > File type > Any;
# - Tool to run on changes: wait-for-aider.sh
# - Output paths to refresh: $Projectpath$
# - [x] autosave, [-] trigger on external, [x] trigger regardless of syntax errors, [-] create output from stdout

repo_root=$(git rev-parse --show-toplevel)
# created in FileWatcher.process_changes, removed in InputOutput.get_input
filename="$repo_root/.aider.working"

has_one_second_passed() {
    local current_time=$(date +%s)
    local time_diff=$((current_time - start_time))
    [ $time_diff -ge 1 ]
}

start_time=$(date +%s)

# wait while the file exists and at least one second has passed so we don't exit immediately
echo "waiting for $filename to be deleted..."

while [ -e "$filename" ] || ! has_one_second_passed; do
    sleep 0.1
done

echo "exiting."
