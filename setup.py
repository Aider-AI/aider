import re

from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

from aider import __version__
from aider.help_pats import exclude_website_pats

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    long_description = re.sub(r"\n!\[.*\]\(.*\)", "", long_description)
    # long_description = re.sub(r"\n- \[.*\]\(.*\)", "", long_description)

# Debug: Print discovered packages
packages = find_packages(exclude=["benchmark"]) + ["aider.website"]
print("Discovered packages:", packages)

import subprocess


cmd = [
    "pip",
    "install",
    "torch<2.2.2",
    "--no-deps",
    "--dry-run",
    "--no-cache-dir",
    "--index-url",
    "https://download.pytorch.org/whl/cpu",
]

result = subprocess.check_output(cmd, text=True)

print(result)

import sys
sys.exit()

setup(
    name="aider-chat",
    version=__version__,
    packages=packages,
    include_package_data=True,
    package_data={
        "aider": ["queries/*.scm"],
        "aider.website": ["**/*.md"],
    },
    exclude_package_data={"aider.website": exclude_website_pats},
    install_requires=requirements,
    python_requires=">=3.9,<3.13",
    entry_points={
        "console_scripts": [
            "aider = aider.main:main",
        ],
    },
    description="Aider is AI pair programming in your terminal",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paul-gauthier/aider",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python",
        "Topic :: Software Development",
    ],
)
