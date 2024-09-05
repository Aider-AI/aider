# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature: Automatically include all non-hidden files when creating a new git repository in a directory with existing files.
- New command-line option `--include-all-files` to explicitly control the inclusion of existing files in new git repositories.
- Enhanced `make_new_repo` and `setup_git` functions to support automatic file inclusion.
