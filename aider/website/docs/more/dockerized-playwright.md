---
parent: More info
nav_order: 300
---

# Dockerized Playwright

Aider can be configured to [use Playwright](/docs/install/optional.html#enable-playwright)
for enhanced web scraping. Playwright only supports recent versions of Windows, macOS, Debian
and Ubuntu.

If you are unable to install Playwright or its dependencies natively, another
option is to run a Playwright server in a Docker container. Note that this is
different from [running the entire Aider in a container](/docs/install/docker.html)
and avoids some limitations of that method.

To do it, first make sure Aider is installed with Playwright support. If you tried
installing Playwright from within Aider itself and it failed when installing browsers,
you are probably good to go. Another way is to install it with the `playwright`
[extra](https://packaging.python.org/en/latest/tutorials/installing-packages/#installing-extras)
for the `aider-chat` Python package.

The next step is to figure out which Playwright library your Aider installation uses.
The major and minor versions of the `playwright` package MUST be the same as the major
and minor versions of the dockerized Playwright server.

Refer to the documentation for your Python package manager of choice for the instructions
on how to install Aider with the `playwright` extra and how to check the version of the
`playwright` Python package. Here are the example commands for `pip`.

```bash
# Install Aider with Playwright support
python -m pip install -U --upgrade-strategy only-if-needed aider-chat[playwright]
```

```bash
# Check Playwright version
python -m pip show playwright
```
```
Name: playwright
Version: 1.52.0
Summary: A high-level API to automate web browsers
...
```

Having done that, run the corresponding Playwright server version using the official
[Docker image](https://mcr.microsoft.com/en-us/artifact/mar/playwright/about). Assuming
you already have Docker installed and running, the following command should work to run
the container in the background. Replace the version (`1.52.0`) of both the container image
and `playwright` package with the version of `playwright` used by Aider. Note that the patch
version (the number after the second period in the version string) is allowed to differ.

```bash
docker run --name playwright_server --rm -d --init \
    -p 3000:3000 --workdir /home/pwuser --user pwuser \
    mcr.microsoft.com/playwright:v1.52.0 \
    npx -y playwright@1.52.0 run-server --port 3000 --host 0.0.0.0
```

Once the container is up, configure Aider to connect to it using the [--playwright-ws-endpoint](/docs/config/options.html#--playwright-ws-endpoint-url)
option. As with any option, you can specify it on the command line, in your YAML
configuration file, or using the corresponding environment variable. Make sure
you do not also have `--disable-playwright` specified.

For example, if you have started the Playwright container on your local machine using the
command above, you can use it in Aider after starting it like this:

```bash
aider --playwright-ws-endpoint ws://127.0.0.1:3000
```

Try the `/web` in-chat command, and if you don't see an error message, Aider is successfully
scraping the web page using the Playwright server.