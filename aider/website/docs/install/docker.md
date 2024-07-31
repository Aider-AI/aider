---
parent: Installation
nav_order: 100
---

# Aider with docker

You can run aider via docker without doing any local installation, like this:

```
docker pull paulgauthier/aider
docker run -it --volume $(pwd):/app paulgauthier/aider --openai-api-key $OPENAI_API_KEY [...other aider args...]
```

You should run the above commands from the root of your git repo,
since the `--volume` arg maps your current directory into the
docker container.
Given that, you need to be in the root of your git repo for aider to be able to
see the repo and all its files.

You should be sure your that
git repo config contains your user name and email, since the
docker container won't have your global git config.
Run these commands while in your git repo, before
you do the `docker run` command:

```
git config user.email "you@example.com"
git config user.name "Your Name"
```

## Full version

The above command installs the aider core, which is missing some of the extra
features like interactive help, the browser GUI and Playwright support for
scraping web pages.

Use `paulgauthier/aider-full` to get all the features, at the expense of a larger
docker image.

```
docker pull paulgauthier/aider-full
docker run -it --volume $(pwd):/app paulgauthier/aider-full --openai-api-key $OPENAI_API_KEY [...other aider args...]
```

## Limitations

- When you use the in-chat `/run` command, it will be running shell commands *inside the docker container*. So those commands won't be running in your local environment, which may make it tricky to `/run` tests, etc for your project.
- The `/voice` command won't work unless you can figure out how to give the docker container access to your host audio device. The container has libportaudio2 installed, so it should work if you can do that.
