---
parent: Usage
nav_order: 800
description: Tell aider to follow your coding conventions when it works on your code.
---
# Specifying coding conventions

Sometimes you want GPT to be aware of certain coding guidelines,
like whether to provide type hints, which libraries or packages
to prefer, etc.

The easiest way to do that with aider is to simply create
a small markdown file and include it in the chat.

For example, say we want our python code to:

```
- Prefer httpx over requests for making http requests.
- Use types everywhere possible.
```

We would simply create a file like `CONVENTIONS.md` with those lines
and then we can add it to the aider chat, along with the file(s)
that we want to edit:

<div class="chat-transcript" markdown="1">
> $ aider CONVENTIONS.md useragent.py  
>  
> Aider v0.24.2-dev  
> Added CONVENTIONS.md to the chat.  
> Added useragent.py to the chat.  

#### write a function that uses httpbin to check the user agent on the request. return the ua.  

To fulfill your request, I will:

1. Add an import for `httpx`.
2. Write a function named `check_user_agent` that makes a GET request to `httpbin.org/user-agent` and returns the user agent string.

Here is the diff for the `useragent.py` file:

```diff
--- useragent.py
+++ useragent.py
@@ ... @@
+import httpx
+
+def check_user_agent() -> str:
+    response = httpx.get('https://httpbin.org/user-agent')
+    return response.json()['user-agent']
```

This function uses `httpx` to make a GET request to `httpbin.org/user-agent`, which returns a JSON response containing the user agent of the HTTP client. The function then extracts the user agent string from the JSON response and returns it.

> Applied edit to useragent.py  
</div>

GPT correctly used `httpx` and provided type hints.
See below for the transcript of this same
coding task conducted *without*
using `CONVENTIONS.md`.
In this case, GPT used `requests` and skipped types,
which is perhaps more typical in small python scripts.

<div class="chat-transcript" markdown="1">
> $ aider useragent.py  
>  
> Aider v0.24.2-dev  
> Added useragent.py to the chat.  


#### write a function that uses httpbin to check the user agent on the request. return the ua.  

```diff
--- /dev/null
+++ useragent.py
@@ ... @@
+import requests
+
+def check_user_agent():
+    response = requests.get('https://httpbin.org/user-agent')
+    user_agent = response.json().get('user-agent')
+    return user_agent
```

> Applied edit to useragent.py  
</div>
