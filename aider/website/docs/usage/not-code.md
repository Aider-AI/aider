---
parent: Usage
nav_order: 901
description: Edit configuration files, documentation, and other text-based formats.
---

# Editing config & text files

Aider isn't just for code! Here are practical examples of modifying common config/text files:

## Shell Configuration
```bash
$ aider .bashrc

Added .bashrc to the chat.
────────────────────────────────────────────────────────────────
.bashrc
> Add an alias 'll' that runs 'ls -alh' and update PATH to include ~/.local/bin

+ alias ll='ls -alh'
+ export PATH="$HOME/.local/bin:$PATH"
```

## SSH Configurations
```bash
$ aider ~/.ssh/config

Added config to the chat.
────────────────────────────────────────────────────────────────
config
> Create a Host entry 'my-server' using bastion.example.com as JumpHost

+ Host my-server
+     HostName 192.168.1.100
+     User deploy
+     Port 2222
+     IdentityFile ~/.ssh/deploy_key
+     ProxyJump bastion.example.com
```

## Docker Setup
```bash
$ aider Dockerfile docker-compose.yml

Added Dockerfile and docker-compose.yml to the chat.
────────────────────────────────────────────────────────────────
Dockerfile
> Set non-root user and enable healthchecks

+ USER appuser
+ HEALTHCHECK --interval=30s --timeout=3s \
+   CMD curl -f http://localhost:8000/health || exit 1

docker-compose.yml
> Expose port 5432 and add volume for postgres data

  services:
    postgres:
      image: postgres:15
+     ports:
+       - "5432:5432"
+     volumes:
+       - pgdata:/var/lib/postgresql/data
```

## Git Configuration
```bash
$ aider .gitconfig

Added .gitconfig to the chat.
────────────────────────────────────────────────────────────────
.gitconfig
> Set default push behavior to current branch and enable color UI

+ [push]
+     default = current
+ [color]
+     ui = auto
```

## System Configuration
```bash
$ aider /etc/hosts  # May need sudo

Added hosts to the chat.
────────────────────────────────────────────────────────────────
hosts
> Block tracking domains by pointing them to 127.0.0.1

+ 127.0.0.1   ads.example.com
+ 127.0.0.1   track.analytics.co
```


## Editor Configs
```bash
$ aider .vimrc

Added .vimrc to the chat.
────────────────────────────────────────────────────────────────
.vimrc
> Enable line numbers and set 4-space tabs for Python

+ set number
+ autocmd FileType python set tabstop=4 shiftwidth=4 expandtab
```

## Application Configuration
```bash
$ aider settings.json

Added settings.json to the chat.
────────────────────────────────────────────────────────────────
settings.json (VSCode)
> Enable auto-format on save and set default formatter

+ "editor.formatOnSave": true,
+ "editor.defaultFormatter": "esbenp.prettier-vscode"
```

## Environment Files
```bash
$ aider .env

Added .env to the chat.
────────────────────────────────────────────────────────────────
.env
> Configure database connection with SSL

+ DB_HOST=db.example.com
+ DB_PORT=5432
+ DB_SSL=true
```

## Markdown Documentation
```bash
$ aider README.md

Added README.md to the chat.
────────────────────────────────────────────────────────────────
README.md
> Add installation section with brew and pip options

+ ## Installation
+ ```bash
+ # Homebrew
+ brew install cool-app-10k
+ 
+ # PyPI
+ pipx install cool-app-10k
+ ```
```

## XML Configuration
```bash
$ aider pom.xml

Added pom.xml to the chat.
────────────────────────────────────────────────────────────────
pom.xml
> Add JUnit 5 dependency with test scope

+ <dependency>
+     <groupId>org.junit.jupiter</groupId>
+     <artifactId>junit-jupiter-api</artifactId>
+     <version>5.9.2</version>
+     <scope>test</scope>
+ </dependency>
```


