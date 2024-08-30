__version__ = "0.54.8-dev"


# This is disabled. Git pre-push hooks won't pick up a new commit with the hash.

"""[[[cog
import subprocess

try:
    git_hash = subprocess.check_output(
        ['git', 'rev-parse', '--short=7', 'HEAD'],
        universal_newlines=True,
        ).strip()
except subprocess.CalledProcessError:
    git_hash = None

cog.out(f'git_hash = "{git_hash}"')
]]]"""
git_hash = None
"""[[[end]]]"""

if "-dev" in __version__ and git_hash:
    xyz = __version__.split("-")[0]
    __version__ = xyz + "-dev+" + git_hash
