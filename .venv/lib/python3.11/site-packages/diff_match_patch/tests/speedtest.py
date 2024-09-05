#!/usr/bin/python3

"""Diff Speed Test
Copyright 2018 The diff-match-patch Authors.
https://github.com/google/diff-match-patch

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import gc
import imp
import os
import sys
import time

parentPath = os.path.abspath("..")
if parentPath not in sys.path:
    sys.path.insert(0, parentPath)
import diff_match_patch as dmp_module

# Force a module reload.  Allows one to edit the DMP module and rerun the test
# without leaving the Python interpreter.
imp.reload(dmp_module)


def main():
    text1 = open("speedtest1.txt").read()
    text2 = open("speedtest2.txt").read()

    dmp = dmp_module.diff_match_patch()
    dmp.Diff_Timeout = 0.0

    # Execute one reverse diff as a warmup.
    dmp.diff_main(text2, text1, False)
    gc.collect()

    start_time = time.time()
    dmp.diff_main(text1, text2, False)
    end_time = time.time()
    print("Elapsed time: %f" % (end_time - start_time))


if __name__ == "__main__":
    main()
