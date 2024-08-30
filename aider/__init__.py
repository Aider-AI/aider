__version__ = "0.54.8-dev"

"""
[[[cog
# TODO: write python to emit `git_hash = "X"`, where X is the latest 7-char git hash
# python goes here
]]]
"""
git_hash = "deadbee"
"""
[[[end]]]
"""

if '-dev' in __version__:
    xyz = __version__.split("-")[0]
    __version__ = xyz + "-dev+" + git_hash
