# Configuration Parameter Handling in Aider

This document outlines how configuration parameters are loaded and processed in the aider project.

## Overview

Aider uses a combination of command-line arguments, environment variables, and configuration files to manage its settings. The project employs the `configargparse` library for argument parsing and the `python-dotenv` library for loading environment variables from `.env` files.

## Key Components

1. **Command-line Arguments**: Defined in `aider/args.py`
2. **Environment Variables**: Loaded from `.env` files
3. **YAML Configuration**: Loaded from `.aider.conf.yml` files

## File Locations

Aider searches for configuration files in the following order:

1. Command-line specified location
2. Current working directory
3. Git repository root
4. User's home directory

## Implementation Details

### Command-line Argument Parsing

- File: `aider/args.py`
- Function: `get_parser()`
- Key Features:
  - Uses `configargparse.ArgumentParser`
  - Automatically handles environment variables with the `AIDER_` prefix
  - Defines all available command-line options

### Environment Variable Loading

- File: `aider/main.py`
- Function: `load_dotenv_files()`
- Key Features:
  - Uses `dotenv.load_dotenv()` to load `.env` files
  - Supports multiple `.env` file locations
  - Overrides existing environment variables

### YAML Configuration

- File: `aider/main.py`
- Function: `main()`
- Key Features:
  - Searches for `.aider.conf.yml` in multiple locations
  - Loads YAML configuration using `configargparse`

## Priority of Configuration Sources

1. Command-line arguments (highest priority)
2. Environment variables (including those from `.env` files)
3. YAML configuration file
4. Default values (lowest priority)

## Special Handling

- OpenAI and Anthropic API keys can be stored in both YAML config and `.env` files
- All other API keys must be specified in environment variables or `.env` files

## Sample Files

- `.env`: `aider/website/assets/sample.env`
- `.aider.conf.yml`: `aider/website/assets/sample.aider.conf.yml`

These sample files provide examples of the expected format and available options for each configuration method.
