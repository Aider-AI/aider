# Aider CLI Tool Environment

This directory provides a Nix Flake configuration for setting up an environment to use the [Aider CLI tool](https://aider.chat/). The environment is configured to ensure all necessary dependencies are available and the `aider` command is ready to use.

## Purpose

The purpose of this flake is to create a reproducible environment for using the Aider CLI tool. By using Nix Flakes, we ensure that the environment is consistent across different machines and setups.

## Usage

In the examples below, replace `<user>` with the GitHub username whose fork you want to use.

1. **Install**:
   Aider and its dependencies are installed into the Python and NodeJS environments
   in the `~/.cache/aider-chat/` directory by running:
   ```sh
   nix develop 'https://github.com/<user>/aider-chat/archive/refs/heads/main.zip#install'
   ```

2. **Run**:
   To launch Aider in the `~/.cache/aider-chat/` environment, type:
   ```sh
   nix develop 'https://github.com/<user>/aider-chat/archive/refs/heads/main.zip'
   ```

3. **Shell**:
   If you want to launch `aider` manually on the command line, you can drop to a shell
   in the Aider environment:
   ```sh
   nix develop 'https://github.com/<user>/aider-chat/archive/refs/heads/main.zip#shell'
   ```
   You can then use the `aider` command as needed. For more information on how to use `aider`, refer to the [Aider CLI tool documentation](https://aider.chat/) and the [GitHub repository](https://github.com/paul-gauthier/aider).

## Configuration Details

The environment is defined in the `flake.nix` file. It includes:
- `libsecret` so API keys can be managed by the desktop keychain
- NodeJS with ESLint installed in `~/.cache/aider-chat/.npm-global/`
- Python 3 and a virtualenv (`~/.cache/aider-chat/.venv/`) that is automatically created and activated.
- The `aider` CLI tool is installed and upgraded within the Python virtualenv.
- The Playwright library (Python version) and supporting browsers. 
- The `PATH` is configured to include the virtual environment's `bin` directory.
- An `aider-install` script is provided for installing and upgrading Aider and its dependencies as well as ESLint.

For more details, refer to the `flake.nix` file in this repository.
