from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

import re

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    long_description = re.sub(r'\n!\[.*\]\(.*\)', '', long_description)
    long_description = re.sub(r'\n- \[.*\]\(#.*\)', '', long_description)

setup(
    name="aider-chat",
    version="0.5.2",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aider = aider.main:main",
        ],
    },
    long_description=long_description,
    long_description_content_type="text/markdown",
)
