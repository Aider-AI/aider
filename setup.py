import re
import subprocess
import sys

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

torch = "torch==2.2.2"
cmd = [
    sys.executable,
    "-m",
    "pip",
    "download",
    torch,
    "--no-deps",
    "--dest",
    "/dev/null",
    "--index-url",
    "https://download.pytorch.org/whl/cpu",
]

pytorch_url = None
try:
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end='')  # Print each line of output
        url_match = re.search(r"Downloading (https://download\.pytorch\.org/[^\s]+\.whl)", line)
        if url_match:
            pytorch_url = url_match.group(1)
            print(f"PyTorch URL: {pytorch_url}")
            process.terminate()  # Terminate the subprocess
            break
    process.wait()  # Wait for the process to finish
except subprocess.CalledProcessError as e:
    print(f"Error running pip download: {e}")

if pytorch_url:
    requirements = [f"torch @ {pytorch_url}"] + requirements
else:
    print("PyTorch URL not found in the output")
    requirements = [torch] + requirements

print(requirements)

# sys.exit()

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
