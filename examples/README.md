# What's it like to code with GPT-4 and aider?

Below are some chat transcripts showing what it's like to code with the help of GPT-4 using the `aider` command-line chat tool.
In the chats, you'll see a varity of coding tasks like generating new code, editing existing code, debugging, exploring unfamiliar code, etc.

* [**Hello World Flask App**](hello-world-flask.md): Creating a simple Flask app with various endpoints, such as adding two numbers and calculating the Fibonacci sequence.

* [**Pong Game with Pygame**](pong.md): Creating a simple Pong game using the Pygame library, with customizations for paddle size and color, and ball speed adjustments.

* [**2048 Game Modification**](2048-game.md): Exploring and modifying an open-source javascript repo for the 2048 game, including adding randomness to the scoring system.

* [**Complex Multi-file Change with Debugging**](complex-change.md): A complex code change involving multiple source files and debugging.

* [**Semantic Search & Replace**](semantic-search-replace.md): Updating a collection of function calls, which requires dealing with various formatting and semantic differences in the various function call sites.

* [**CSS Exercise: Animation Dropdown Menu**](css-exercises.md): A small CSS exercise involving adding animation to a dropdown menu.

* [**Automatically Update Docs**](update-docs.md): Automatically updating documentation based on the latest version of the main() function.

* [**Editing an Asciinema Cast File**](asciinema.md): Editing escape sequences in an `asciinema` screencast file.

## What's happening in these chats?

To better understand the chat transcripts, it's worth knowing that:

  - Each time GPT-4 suggests a code change, `aider` automatically applies it to the source files.
  - After applying the edits, `aider` commits them to git with a descriptive commit message.
  - GPT-4 can only see and edit files which have been "added to the chat session". The user adds files either via the command line or the in-chat `/add` command. If GPT-4 asks to see specific files, `aider` asks the user for permission to add them to the chat. The transcripts contain notifications from `aider` whenever a file is added or dropped from the session.

## Transcript formatting

> This is output from the aider tool.

#### These are chat messages written by the user.

Chat responses from GPT-4 are in a plain font like this, and often include colorized "edit blocks" that specify edits to the code.
Here's a sample edit block that switches from printing "hello" to "goodbye":

```python
hello.py
<<<<<<< ORIGINAL
print("hello")
=======
print("goodbye")
>>>>>>> UPDATED
```
