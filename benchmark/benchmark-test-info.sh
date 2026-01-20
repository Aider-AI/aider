#!/usr/bin/env bash

aider_results_to_cols() {
  jq -j '.cost, ", ", .duration, ", ", .test_timeouts, ", ", .num_error_outputs, ", ", .num_user_asks, ", ", .num_exhausted_context_windows, ", ", .num_malformed_responses, ", ", .syntax_errors, ", ", .indentation_errors, ", ", .lazy_comments' \
    "$1"
}

benchmark_ls() {
    test "$1" || { echo "Usage: benchmark.ls <benchmark-run-dir>" ; return 1;}
    local benchmark_run_dir="$1"

    echo "# -dirname $(basename "$benchmark_run_dir") tests"
    echo 'failed-run-count (negative if all attempts failed), test-name, cost, duration, test_timeouts, num_error_outputs, num_user_asks, num_exhausted_context_windows, num_malformed_responses, syntax_errors, indentation_errors, lazy_comments'
    i=0 failures=0 failed_test_count=0
    while IFS= read -r -d '' file; do
        (( i+=1 ))
        outcome="$(jq -rc '.tests_outcomes' "$file" | tr -d '[]')"
        test "$outcome" = true && \
          attempts=0 || \
          attempts=$(echo "$outcome" | tr ',' '\n' | grep -c "false")
        ((failures+=attempts))
        dir_name="$(basename "$(dirname "$file")")"
        # If no attempt succeeded, make 'attempts' negative and inc failed_test_count
        echo "$outcome" | grep -q "true" || \
            ((attempts=-attempts, failed_test_count+=1))
        printf '%2d, %s, %s\n' "$attempts" "$dir_name" "$( aider_results_to_cols "$file" )"
    done < <(find "$benchmark_run_dir" -name '.aider.results.json' -print0 | sort -z)

    printf 'Failed tests: %03.1f%% ( %i / %i )\n' $((100. * failed_test_count / i)) $failed_test_count $i
    echo "Failed runs : $failures"
}
alias benchmark.ls=benchmark_ls "$@"
test "$#" -eq 0 || \
  benchmark_ls "$@"
