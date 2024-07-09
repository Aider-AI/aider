import re
import subprocess
import sys

from setuptools import find_packages, setup

from aider import __version__
from aider.help_pats import exclude_website_pats


# Find the torch requirement and replace it with the CPU only version,
# because the GPU versions are huge
def get_requirements():
    with open("requirements.txt") as f:
        requirements = f.read().splitlines()

    requirements = [line for line in requirements if not line.startswith("---extra-index-url")]

    torch = next((req for req in requirements if req.startswith("torch==")), None)
    if not torch:
        return requirements

    pytorch_url = None

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        torch,
        "--no-deps",
        "--dry-run",
        # "--no-cache-dir",
        # "--dest",
        # temp_dir,
        "--index-url",
        "https://download.pytorch.org/whl/cpu",
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            url_match = re.search(r"Downloading (https://download\.pytorch\.org/[^\s]+\.whl)", line)
            if url_match:
                pytorch_url = url_match.group(1)

            if pytorch_url:
                process.terminate()  # Terminate the subprocess
                break

        process.wait()  # Wait for the process to finish
    except subprocess.CalledProcessError as e:
        print(f"Error running pip download: {e}")

    # print(pytorch_url)
    # sys.exit()

    if pytorch_url:
        requirements.remove(torch)
        requirements = [f"torch @ {pytorch_url}"] + requirements

    return requirements


requirements = get_requirements()

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
