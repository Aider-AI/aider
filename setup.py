from setuptools import setup, find_packages

setup(
    name="aider",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "prompt_toolkit",
        "pygments",
        "rich",
        "fastapi",
        "uvicorn",
        "packaging"
    ]
)