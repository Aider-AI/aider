---
title: Release history
parent: More info
nav_order: 999
---

<!--[[[cog
# This page is a copy of HISTORY.md, adding the front matter above.
text = open("HISTORY.md").read()
cog.out(text)
]]]-->

# Release history

### v0.39.0

- Use `--sonnet` for Claude 3.5 Sonnet, which is the top model on [aider's LLM code editing leaderboard](https://aider.chat/docs/leaderboards/#claude-35-sonnet-takes-the-top-spot).
- All `AIDER_xxx` environment variables can now be set in `.env` (by @jpshack-at-palomar).
- Use `--llm-history-file` to log raw messages sent to the LLM (by @daniel-vainsencher).
- Commit messages are no longer prefixed with "aider:". Instead the git author and committer names have "(aider)" added.

### v0.38.0

- Use `--vim` for [vim keybindings](https://aider.chat/docs/commands.html#vi) in the chat.
- [Add LLM metadata](https://aider.chat/docs/llms/warnings.html#specifying-context-window-size-and-token-costs) via `.aider.models.json` file (by @caseymcc).
- More detailed [error messages on token limit errors](https://aider.chat/docs/troubleshooting/token-limits.html).
- Single line commit messages, without the recent chat messages.
- Ensure `--commit --dry-run` does nothing.
- Have playwright wait for idle network to better scrape js sites.
- Documentation updates, moved into website/ subdir.
- Moved tests/ into aider/tests/.

### v0.37.0

- Repo map is now optimized based on text of chat history as well as files added to chat.
- Improved prompts when no files have been added to chat to solicit LLM file suggestions.
- Aider will notice if you paste a URL into the chat, and offer to scrape it.
- Performance improvements the repo map, especially in large repos.
- Aider will not offer to add bare filenames like `make` or `run` which may just be words.
- Properly override `GIT_EDITOR` env for commits if it is already set.
- Detect supported audio sample rates for `/voice`.
- Other small bug fixes.

### v0.36.0

- [Aider can now lint your code and fix any errors](https://aider.chat/2024/05/22/linting.html).
  - Aider automatically lints and fixes after every LLM edit.
  - You can manually lint-and-fix files with `/lint` in the chat or `--lint` on the command line.
  - Aider includes built in basic linters for all supported tree-sitter languages.
  - You can also configure aider to use your preferred linter with `--lint-cmd`.
- Aider has additional support for running tests and fixing problems.
  - Configure your testing command with `--test-cmd`.
  - Run tests with `/test` or from the command line with `--test`.
  - Aider will automatically attempt to fix any test failures.
  

### v0.35.0

- Aider now uses GPT-4o by default.
  - GPT-4o tops the [aider LLM code editing leaderboard](https://aider.chat/docs/leaderboards/) at 72.9%, versus 68.4% for Opus.
  - GPT-4o takes second on [aider's refactoring leaderboard](https://aider.chat/docs/leaderboards/#code-refactoring-leaderboard) with 62.9%, versus Opus at 72.3%.
- Added `--restore-chat-history` to restore prior chat history on launch, so you can continue the last conversation.
- Improved reflection feedback to LLMs using the diff edit format.
- Improved retries on `httpx` errors.

### v0.34.0

- Updated prompting to use more natural phrasing about files, the git repo, etc. Removed reliance on read-write/read-only terminology.
- Refactored prompting to unify some phrasing across edit formats.
- Enhanced the canned assistant responses used in prompts.
- Added explicit model settings for `openrouter/anthropic/claude-3-opus`, `gpt-3.5-turbo`
- Added `--show-prompts` debug switch.
- Bugfix: catch and retry on all litellm exceptions.


### v0.33.0

- Added native support for [Deepseek models](https://aider.chat/docs/llms.html#deepseek) using `DEEPSEEK_API_KEY` and `deepseek/deepseek-chat`, etc rather than as a generic OpenAI compatible API.

### v0.32.0

- [Aider LLM code editing leaderboards](https://aider.chat/docs/leaderboards/) that rank popular models according to their ability to edit code.
  - Leaderboards include GPT-3.5/4 Turbo, Opus, Sonnet, Gemini 1.5 Pro, Llama 3, Deepseek Coder & Command-R+.
- Gemini 1.5 Pro now defaults to a new diff-style edit format (diff-fenced), enabling it to work better with larger code bases.
- Support for Deepseek-V2, via more a flexible config of system messages in the diff edit format.
- Improved retry handling on errors from model APIs.
- Benchmark outputs results in YAML, compatible with leaderboard.

### v0.31.0

- [Aider is now also AI pair programming in your browser!](https://aider.chat/2024/05/02/browser.html) Use the `--browser` switch to launch an experimental browser based version of aider.
- Switch models during the chat with `/model <name>` and search the list of available models with `/models <query>`.

### v0.30.1

- Adding missing `google-generativeai` dependency

### v0.30.0

- Added [Gemini 1.5 Pro](https://aider.chat/docs/llms.html#free-models) as a recommended free model.
- Allow repo map for "whole" edit format.
- Added `--models <MODEL-NAME>` to search the available models.
- Added `--no-show-model-warnings` to silence model warnings.

### v0.29.2

- Improved [model warnings](https://aider.chat/docs/llms.html#model-warnings) for unknown or unfamiliar models

### v0.29.1

- Added better support for groq/llama3-70b-8192

### v0.29.0

- Added support for [directly connecting to Anthropic, Cohere, Gemini and many other LLM providers](https://aider.chat/docs/llms.html).
- Added `--weak-model <model-name>` which allows you to specify which model to use for commit messages and chat history summarization.
- New command line switches for working with popular models:
  - `--4-turbo-vision`
  - `--opus`
  - `--sonnet`
  - `--anthropic-api-key`
- Improved "whole" and "diff" backends to better support [Cohere's free to use Command-R+ model](https://aider.chat/docs/llms.html#cohere).
- Allow `/add` of images from anywhere in the filesystem.
- Fixed crash when operating in a repo in a detached HEAD state.
- Fix: Use the same default model in CLI and python scripting.

### v0.28.0

- Added support for new `gpt-4-turbo-2024-04-09` and `gpt-4-turbo` models.
  - Benchmarked at 61.7% on Exercism benchmark, comparable to `gpt-4-0613` and worse than the `gpt-4-preview-XXXX` models. See [recent Exercism benchmark results](https://aider.chat/2024/03/08/claude-3.html).
  - Benchmarked at 34.1% on the refactoring/laziness benchmark, significantly worse than the `gpt-4-preview-XXXX` models. See [recent refactor bencmark results](https://aider.chat/2024/01/25/benchmarks-0125.html).
  - Aider continues to default to `gpt-4-1106-preview` as it performs best on both benchmarks, and significantly better on the refactoring/laziness benchmark.

### v0.27.0

- Improved repomap support for typescript, by @ryanfreckleton.
- Bugfix: Only /undo the files which were part of the last commit, don't stomp other dirty files
- Bugfix: Show clear error message when OpenAI API key is not set.
- Bugfix: Catch error for obscure languages without tags.scm file.

### v0.26.1

- Fixed bug affecting parsing of git config in some environments.

### v0.26.0

- Use GPT-4 Turbo by default.
- Added `-3` and `-4` switches to use GPT 3.5 or GPT-4 (non-Turbo).
- Bug fix to avoid reflecting local git errors back to GPT.
- Improved logic for opening git repo on launch.

### v0.25.0

- Issue a warning if user adds too much code to the chat.
  - https://aider.chat/docs/faq.html#how-can-i-add-all-the-files-to-the-chat
- Vocally refuse to add files to the chat that match `.aiderignore`
  - Prevents bug where subsequent git commit of those files will fail.
- Added `--openai-organization-id` argument.
- Show the user a FAQ link if edits fail to apply.
- Made past articles part of https://aider.chat/blog/

### v0.24.1

- Fixed bug with cost computations when --no-steam in effect

### v0.24.0

- New `/web <url>` command which scrapes the url, turns it into fairly clean markdown and adds it to the chat.
- Updated all OpenAI model names, pricing info
- Default GPT 3.5 model is now `gpt-3.5-turbo-0125`.
- Bugfix to the `!` alias for `/run`.

### v0.23.0

- Added support for `--model gpt-4-0125-preview` and OpenAI's alias `--model gpt-4-turbo-preview`. The `--4turbo` switch remains an alias for `--model gpt-4-1106-preview` at this time.
- New `/test` command that runs a command and adds the output to the chat on non-zero exit status.
- Improved streaming of markdown to the terminal.
- Added `/quit` as alias for `/exit`.
- Added `--skip-check-update` to skip checking for the update on launch.
- Added `--openrouter` as a shortcut for `--openai-api-base https://openrouter.ai/api/v1`
- Fixed bug preventing use of env vars `OPENAI_API_BASE, OPENAI_API_TYPE, OPENAI_API_VERSION, OPENAI_API_DEPLOYMENT_ID`.

### v0.22.0

- Improvements for unified diff editing format.
- Added ! as an alias for /run.
- Autocomplete for /add and /drop now properly quotes filenames with spaces.
- The /undo command asks GPT not to just retry reverted edit.

### v0.21.1

- Bugfix for unified diff editing format.
- Added --4turbo and --4 aliases for --4-turbo.

### v0.21.0

- Support for python 3.12.
- Improvements to unified diff editing format.
- New `--check-update` arg to check if updates are available and exit with status code.

### v0.20.0

- Add images to the chat to automatically use GPT-4 Vision, by @joshuavial

- Bugfixes:
  - Improved unicode encoding for `/run` command output, by @ctoth
  - Prevent false auto-commits on Windows, by @ctoth

### v0.19.1

- Removed stray debug output.

### v0.19.0

- [Significantly reduced "lazy" coding from GPT-4 Turbo due to new unified diff edit format](https://aider.chat/docs/unified-diffs.html)
  - Score improves from 20% to 61% on new "laziness benchmark".
  - Aider now uses unified diffs by default for `gpt-4-1106-preview`.
- New `--4-turbo` command line switch as a shortcut for `--model gpt-4-1106-preview`.

### v0.18.1

- Upgraded to new openai python client v1.3.7.

### v0.18.0

- Improved prompting for both GPT-4 and GPT-4 Turbo.
  - Far fewer edit errors from GPT-4 Turbo (`gpt-4-1106-preview`).
  - Significantly better benchmark results from the June GPT-4 (`gpt-4-0613`). Performance leaps from 47%/64% up to 51%/71%.
- Fixed bug where in-chat files were marked as both read-only and ready-write, sometimes confusing GPT.
- Fixed bug to properly handle repos with submodules.

### v0.17.0

- Support for OpenAI's new 11/06 models:
  - gpt-4-1106-preview with 128k context window
  - gpt-3.5-turbo-1106 with 16k context window
- [Benchmarks for OpenAI's new 11/06 models](https://aider.chat/docs/benchmarks-1106.html)
- Streamlined [API for scripting aider, added docs](https://aider.chat/docs/faq.html#can-i-script-aider)
- Ask for more concise SEARCH/REPLACE blocks. [Benchmarked](https://aider.chat/docs/benchmarks.html) at 63.9%, no regression.
- Improved repo-map support for elisp.
- Fixed crash bug when `/add` used on file matching `.gitignore`
- Fixed misc bugs to catch and handle unicode decoding errors.

### v0.16.3

- Fixed repo-map support for C#.

### v0.16.2

- Fixed docker image.

### v0.16.1

- Updated tree-sitter dependencies to streamline the pip install process

### v0.16.0

- [Improved repository map using tree-sitter](https://aider.chat/docs/repomap.html)
- Switched from "edit block" to "search/replace block", which reduced malformed edit blocks. [Benchmarked](https://aider.chat/docs/benchmarks.html) at 66.2%, no regression.
- Improved handling of malformed edit blocks targeting multiple edits to the same file. [Benchmarked](https://aider.chat/docs/benchmarks.html) at 65.4%, no regression.
- Bugfix to properly handle malformed `/add` wildcards.


### v0.15.0

- Added support for `.aiderignore` file, which instructs aider to ignore parts of the git repo.
- New `--commit` cmd line arg, which just commits all pending changes with a sensible commit message generated by gpt-3.5.
- Added universal ctags and multiple architectures to the [aider docker image](https://aider.chat/docs/docker.html)
- `/run` and `/git` now accept full shell commands, like: `/run (cd subdir; ls)`
- Restored missing `--encoding` cmd line switch.

### v0.14.2

- Easily [run aider from a docker image](https://aider.chat/docs/docker.html)
- Fixed bug with chat history summarization.
- Fixed bug if `soundfile` package not available.

### v0.14.1

- /add and /drop handle absolute filenames and quoted filenames
- /add checks to be sure files are within the git repo (or root)
- If needed, warn users that in-chat file paths are all relative to the git repo
- Fixed /add bug in when aider launched in repo subdir
- Show models supported by api/key if requested model isn't available

### v0.14.0

- [Support for Claude2 and other LLMs via OpenRouter](https://aider.chat/docs/faq.html#accessing-other-llms-with-openrouter) by @joshuavial
- Documentation for [running the aider benchmarking suite](https://github.com/paul-gauthier/aider/tree/main/benchmark)
- Aider now requires Python >= 3.9


### v0.13.0

- [Only git commit dirty files that GPT tries to edit](https://aider.chat/docs/faq.html#how-did-v0130-change-git-usage)
- Send chat history as prompt/context for Whisper voice transcription
- Added `--voice-language` switch to constrain `/voice` to transcribe to a specific language
- Late-bind importing `sounddevice`, as it was slowing down aider startup
- Improved --foo/--no-foo switch handling for command line and yml config settings

### v0.12.0

- [Voice-to-code](https://aider.chat/docs/voice.html) support, which allows you to code with your voice.
- Fixed bug where /diff was causing crash.
- Improved prompting for gpt-4, refactor of editblock coder.
- [Benchmarked](https://aider.chat/docs/benchmarks.html) at 63.2% for gpt-4/diff, no regression.

### v0.11.1

- Added a progress bar when initially creating a repo map.
- Fixed bad commit message when adding new file to empty repo.
- Fixed corner case of pending chat history summarization when dirty committing.
- Fixed corner case of undefined `text` when using `--no-pretty`.
- Fixed /commit bug from repo refactor, added test coverage.
- [Benchmarked](https://aider.chat/docs/benchmarks.html) at 53.4% for gpt-3.5/whole (no regression).

### v0.11.0

- Automatically summarize chat history to avoid exhausting context window.
- More detail on dollar costs when running with `--no-stream`
- Stronger GPT-3.5 prompt against skipping/eliding code in replies (51.9% [benchmark](https://aider.chat/docs/benchmarks.html), no regression)
- Defend against GPT-3.5 or non-OpenAI models suggesting filenames surrounded by asterisks.
- Refactored GitRepo code out of the Coder class.

### v0.10.1

- /add and /drop always use paths relative to the git root
- Encourage GPT to use language like "add files to the chat" to ask users for permission to edit them.

### v0.10.0

- Added `/git` command to run git from inside aider chats.
- Use Meta-ENTER (Esc+ENTER in some environments) to enter multiline chat messages.
- Create a `.gitignore` with `.aider*` to prevent users from accidentaly adding aider files to git.
- Check pypi for newer versions and notify user.
- Updated keyboard interrupt logic so that 2 ^C in 2 seconds always forces aider to exit.
- Provide GPT with detailed error if it makes a bad edit block, ask for a retry.
- Force `--no-pretty` if aider detects it is running inside a VSCode terminal.
- [Benchmarked](https://aider.chat/docs/benchmarks.html) at 64.7% for gpt-4/diff (no regression)


### v0.9.0

- Support for the OpenAI models in [Azure](https://aider.chat/docs/faq.html#azure)
- Added `--show-repo-map`
- Improved output when retrying connections to the OpenAI API
- Redacted api key from `--verbose` output
- Bugfix: recognize and add files in subdirectories mentioned by user or GPT
- [Benchmarked](https://aider.chat/docs/benchmarks.html) at 53.8% for gpt-3.5-turbo/whole (no regression)

### v0.8.3

- Added `--dark-mode` and `--light-mode` to select colors optimized for terminal background
- Install docs link to [NeoVim plugin](https://github.com/joshuavial/aider.nvim) by @joshuavial
- Reorganized the `--help` output
- Bugfix/improvement to whole edit format, may improve coding editing for GPT-3.5
- Bugfix and tests around git filenames with unicode characters
- Bugfix so that aider throws an exception when OpenAI returns InvalidRequest
- Bugfix/improvement to /add and /drop to recurse selected directories
- Bugfix for live diff output when using "whole" edit format

### v0.8.2

- Disabled general availability of gpt-4 (it's rolling out, not 100% available yet)

### v0.8.1

- Ask to create a git repo if none found, to better track GPT's code changes
- Glob wildcards are now supported in `/add` and `/drop` commands
- Pass `--encoding` into ctags, require it to return `utf-8`
- More robust handling of filepaths, to avoid 8.3 windows filenames
- Added [FAQ](https://aider.chat/docs/faq.html)
- Marked GPT-4 as generally available
- Bugfix for live diffs of whole coder with missing filenames
- Bugfix for chats with multiple files
- Bugfix in editblock coder prompt

### v0.8.0

- [Benchmark comparing code editing in GPT-3.5 and GPT-4](https://aider.chat/docs/benchmarks.html)
- Improved Windows support:
  - Fixed bugs related to path separators in Windows
  - Added a CI step to run all tests on Windows
- Improved handling of Unicode encoding/decoding
  - Explicitly read/write text files with utf-8 encoding by default (mainly benefits Windows)
  - Added `--encoding` switch to specify another encoding
  - Gracefully handle decoding errors
- Added `--code-theme` switch to control the pygments styling of code blocks (by @kwmiebach)
- Better status messages explaining the reason when ctags is disabled

### v0.7.2:

- Fixed a bug to allow aider to edit files that contain triple backtick fences.

### v0.7.1:

- Fixed a bug in the display of streaming diffs in GPT-3.5 chats

### v0.7.0:

- Graceful handling of context window exhaustion, including helpful tips.
- Added `--message` to give GPT that one instruction and then exit after it replies and any edits are performed.
- Added `--no-stream` to disable streaming GPT responses.
  - Non-streaming responses include token usage info.
  - Enables display of cost info based on OpenAI advertised pricing.
- Coding competence benchmarking tool against suite of programming tasks based on Execism's python repo.
  - https://github.com/exercism/python
- Major refactor in preparation for supporting new function calls api.
- Initial implementation of a function based code editing backend for 3.5.
  - Initial experiments show that using functions makes 3.5 less competent at coding.
- Limit automatic retries when GPT returns a malformed edit response.

### v0.6.2

* Support for `gpt-3.5-turbo-16k`, and all OpenAI chat models
* Improved ability to correct when gpt-4 omits leading whitespace in code edits
* Added `--openai-api-base` to support API proxies, etc.

### v0.5.0

- Added support for `gpt-3.5-turbo` and `gpt-4-32k`.
- Added `--map-tokens` to set a token budget for the repo map, along with a PageRank based algorithm for prioritizing which files and identifiers to include in the map.
- Added in-chat command `/tokens` to report on context window token usage.
- Added in-chat command `/clear` to clear the conversation history.
<!--[[[end]]]-->
