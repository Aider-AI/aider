---
parent: Configuration
nav_order: 100
description: How to configure a custom editor for aider's /editor command
---

# Editor configuration

Aider allows you to configure your preferred text editor for use with the `/editor` command. The editor must be capable of running in "blocking mode", meaning the command line will wait until you close the editor before proceeding.

## Using `--editor`

You can specify the text editor with the `--editor` switch or using
`editor:` in aider's
[yaml config file](https://aider.chat/docs/config/aider_conf.html).

## Environment variables

Aider checks the following environment variables in order to determine which editor to use:

1. `AIDER_EDITOR`
2. `VISUAL`
3. `EDITOR`

## Default behavior

If no editor is configured, aider will use these platform-specific defaults:

- Windows: `notepad`
- macOS: `vim`
- Linux/Unix: `vi`

## Using a custom editor

You can set your preferred editor in your shell's configuration file (e.g., `.bashrc`, `.zshrc`):

```bash
export AIDER_EDITOR=vim
```

## Popular Editors by Platform

### macOS

1. **vim**
   ```bash
   export AIDER_EDITOR=vim
   ```

2. **Emacs**
   ```bash
   export AIDER_EDITOR=emacs
   ```

3. **VSCode**
   ```bash
   export AIDER_EDITOR="code --wait"
   ```

4. **Sublime Text**
   ```bash
   export AIDER_EDITOR="subl --wait"
   ```

5. **BBEdit**
   ```bash
   export AIDER_EDITOR="bbedit --wait"
   ```

### Linux

1. **vim**
   ```bash
   export AIDER_EDITOR=vim
   ```

2. **Emacs**
   ```bash
   export AIDER_EDITOR=emacs
   ```

3. **nano**
   ```bash
   export AIDER_EDITOR=nano
   ```

4. **VSCode**
   ```bash
   export AIDER_EDITOR="code --wait"
   ```

5. **Sublime Text**
   ```bash
   export AIDER_EDITOR="subl --wait"
   ```

### Windows

1. **Notepad**
   ```bat
   set AIDER_EDITOR=notepad
   ```

2. **VSCode**
   ```bat
   set AIDER_EDITOR="code --wait"
   ```

3. **Notepad++**
   ```bat
   set AIDER_EDITOR="notepad++ -multiInst -notabbar -nosession -noPlugin -waitForClose"
   ```

## Editor command arguments

Some editors require specific command-line arguments to operate in blocking mode. The `--wait` flag (or equivalent) is commonly used to make the editor block until the file is closed.

## Troubleshooting

If you encounter issues with your editor not blocking (returning to the prompt immediately), verify that:

1. Your editor supports blocking mode
2. You've included the necessary command-line arguments for blocking mode
3. The editor command is properly quoted if it contains spaces or special characters, e.g.:
   ```bash
   export AIDER_EDITOR="code --wait"
   ```
