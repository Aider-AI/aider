#!/bin/bash

# exit when any command fails
set -e

./benchmark/benchmark.py --stats \
      2023-06-29-11-04-31--gpt-3.5-turbo-0301 \
      2023-06-29-11-17-32--gpt-3.5-turbo-0613 \
      2023-06-29-22-18-10--diff-func-string-accept-lists \
      2023-06-29-22-33-14--whole-func \
      2023-06-29-22-33-21--whole-func-string \
      2023-06-30-02-39-48--0613-diff \
      2023-06-30-02-59-11--0301-diff \
      2023-06-30-03-53-55--gpt-3.5-turbo-16k-0613-diff \
      2023-06-30-04-34-00--gpt-3.5-turbo-16k-0613-diff-func-string \
      2023-06-30-05-02-45--gpt-3.5-turbo-16k-0613-whole \
      2023-06-30-05-08-40--gpt-3.5-turbo-16k-0613-whole-func \
      2023-06-30-05-31-44--gpt-4-0314-whole \
      2023-06-30-05-43-54--gpt-4-0314-diff \
      2023-06-30-06-06-02--gpt-4-0613-diff-func-string \
      2023-06-30-06-19-22--gpt-4-0613-whole \
      2023-06-30-13-09-51--gpt-4-0613-diff \
      2023-06-30-13-28-09--gpt-4-0613-whole-func \
      2023-06-30-17-05-20--gpt-3.5-0613-whole-repeat-1 \
      2023-06-30-17-17-42--gpt-3.5-0613-whole-repeat-2 \
      2023-06-30-17-27-04--gpt-3.5-0613-whole-repeat-3 \
      2023-06-30-17-35-07--gpt-3.5-0613-whole-repeat-4 \
      2023-06-30-17-46-25--gpt-3.5-0613-whole-repeat-5

