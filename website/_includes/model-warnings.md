

Aider tries to sanity check that it is configured correctly
to work with the LLM you specified:

- It checks to see that all required environment variables are set for the model. These variables are required to configure things like API keys, API base URLs, etc.
These settings are required to be correct.
- It checks a metadata database to look up the context window size and token costs for the model.
It's usually OK if this extra metadata isn't available.

Sometimes one or both of these checks will fail, so aider will issue
some of the following warnings.

## Missing environment variables

```
Model azure/gpt-4-turbo: Missing these environment variables:
- AZURE_API_BASE
- AZURE_API_VERSION
- AZURE_API_KEY
```

You need to set the listed environment variables.
Otherwise you will get error messages when you start chatting with the model.


## Unknown which environment variables are required

```
Model gpt-5: Unknown which environment variables are required.
```

Aider is unable verify the environment because it doesn't know
which variables are required for the model.
If required variables are missing,
you may get errors when you attempt to chat with the model.
You can look in the
[litellm provider documentation](https://docs.litellm.ai/docs/providers)
to see if the required variables are listed there.

## Context window size and token costs unavailable.

```
Model foobar: Unknown model, context window size and token costs unavailable.
```

If you specify a model that aider has never heard of, you will get an
"unknown model" warning.
This means aider doesn't know the context window size and token costs
for that model.
Some minor functionality will be limited when using such models, but
it's not really a significant problem.

Aider will also try to suggest similarly named models,
in case you made a typo or mistake when specifying the model name.


