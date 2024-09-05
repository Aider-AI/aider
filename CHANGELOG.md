# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature: Automatically include all non-hidden files when creating a new git repository in a directory with existing files.
- New command-line option `--include-all-files` to explicitly control the inclusion of existing files in new git repositories.
- Enhanced `make_new_repo` and `setup_git` functions to support automatic file inclusion.
- Implemented automatic repository scanning and commit functionality after each coder run.
- Added `scan_repo_changes` method to `GitRepo` class to detect and stage new, changed, and deleted files.
- Updated `main` function to call `scan_repo_changes` after each coder run.
- Improved error handling and user feedback for git operations.
- Enhanced git integration to provide more seamless version control during aider sessions.
