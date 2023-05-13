# Using `aider` chat to code with GPT-4

Below are some example chat transcripts that show how you can chat with
the `aider` command line tool
to generate and edit code with GPT-4.

There are a few things worth taking note of:

  - `aider` will add certain source files to the chat session. Once added, these files are available for review and editing by GPT-4. Sometimes the files are added directly from the command line. Other times GPT-4 requests to see other files in the repo, and they are added after the user approves.
  - Code edits proposed by GPT-4 are applied to the source files by `aider`.
  - After applying the edits, `aider` will commit them to git with a senisble commit message.

## Example chat transcripts

There are a varity of example coding chat sessions included,
accomplishing both greenfield generation of new code as well as simple and complex edits to larger codebases:

* [Hello World Flask App](hello-world-flask.md): This example demonstrates how to create a simple Flask app with various endpoints, such as adding two numbers and calculating the Fibonacci sequence.

* [2048 Game Modification](2048-game.md): This example demonstrates how to explore and modify an open-source javascript 2048 game codebase, including adding randomness to the scoring system.

* [Pong Game with Pygame](pong.md): This example demonstrates how to create a simple Pong game using the Pygame library, with customizations for paddle size and color, and ball speed adjustments.

* [Complex Multi-file Change with Debugging](complex-change.md): This example demonstrates a complex code change involving multiple source files and debugging with the help of `aider`.

* [Semantic Search & Replace](semantic-search-replace.md): This example showcases `aider` performing semantic search and replace operations in code, dealing with various formatting and semantic differences in the function calls that it updates.

* [CSS Exercise: Animation Dropdown Menu](css-exercises.md): This example demonstrates how to complete a CSS exercise involving adding animation to a dropdown menu, creating a bounce illusion when the dropdown expands close to its final end state.

* [Automatically Update Docs](update-docs.md): This example demonstrates how to use `aider` to automatically update documentation based on the latest version of the main() function in the code.

## Transcript formatting

#### > The user's chat messages are bold and shown on a prompt line. They contain they user's change requests, clarifications, etc.

> Output from the aider tool is shown in a blockquote

Responses from GPT-4 are in a plain font, and often include colorized code blocks that specify edits to the code.

