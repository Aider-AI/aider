import json
import os
import sys

"""
Example of a callback script in Python for Aider.
"""

script_dir = os.path.dirname(os.path.realpath(__file__))
params = json.loads(sys.argv[1])

with open(f"{script_dir}/aider_callback_params.json", "w") as f:
    json.dump(params, f, indent=2)
