import re

from setuptools import find_packages, setup

from aider import __version__
from aider.help_pats import exclude_website_pats


def get_requirements(suffix=""):
    fname = "requirements" + suffix + ".txt"
    with open(fname) as f:
        requirements = f.read().splitlines()
    return requirements


requirements = get_requirements()
dev_requirements = get_requirements("-dev")
hf_requirements = get_requirements("-hf-embed")

# README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    long_description = re.sub(r"\n!\[.*\]\(.*\)", "", long_description)
    # long_description = re.sub(r"\n- \[.*\]\(.*\)", "", long_description)

# Discover packages, plus the website
packages = find_packages(exclude=["benchmark"]) + ["aider.website"]
print("Discovered packages:", packages)

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
    extras_require={
        "dev": dev_requirements,
        "hf-embed": hf_requirements,
    },
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
