__version__ = "0.54.8-dev"

"""
[[[cog
import subprocess

try:
    git_hash = subprocess.check_output(['git', 'rev-parse', '--short=7', 'HEAD'], universal_newlines=True).strip()
except subprocess.CalledProcessError:
    git_hash = ""

print(f'git_hash = "{git_hash}"')
]]]
"""
git_hash = "deadbee"  # This line will be replaced by cog
"""
[[[end]]]
"""

if '-dev' in __version__:
    xyz = __version__.split("-")[0]
    __version__ = xyz + "-dev+" + git_hash
