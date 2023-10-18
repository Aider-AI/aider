
# Running aider with docker (experimental)

You can run aider via docker without doing any local installation, like this:

```
docker pull paulgauthier/aider
docker run -it --volume `pwd`:/app paulgauthier/aider --openai-api-key $OPENAI_API_KEY <...add other aider args...>
```

You should run the above commands from the root of your git repo,
since the `--volume `pwd`:/app` maps the current directory into the
docker container.
You need to be in the root of your git repo for aider to be able to
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

Be aware that when you use the in-chat `/run` command, it will
be running shell commands *inside the docker container*.
So those commands won't be running in your local environment,
which may make it tricky to `/run` tests, etc for your project.
