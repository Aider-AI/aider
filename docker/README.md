
# Running aider with docker (experimental)

You can run aider via docker without doing any local installation, like this:


```
docker run -it --volume `pwd`:/app paulgauthier/aider
```

You will also need to pass in your `OPENAI_API_KEY`, which can be done with the `--openai-api-key` argument:


```
docker run -it --volume `pwd`:/app paulgauthier/aider --openai-api-key $OPENAI_API_KEY
```

You should run the above commands from the root of your git repo.

You should be sure your that
git repo config contains your user name and email, since the
docker container won't have your global git config:

```
git config user.email "you@example.com"
git config user.name "Your Name"
```  

Be aware that when you use the in-chat `/run` command, it will
be running shell commands *inside the docker container*.
So those commands won't be running in your local environment,
which may make it tricky to `/run` tests, etc for your project.
