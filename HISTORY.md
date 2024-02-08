# Release history

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
- Improved handling of malformed edit blocks targetting multiple edits to the same file. [Benchmarked](https://aider.chat/docs/benchmarks.html) at 65.4%, no regression.
- Bugfix to properly handle malformed `/add` wildcards.


### v0.15.0

- Added support for `.aiderignore` file, which instructs aider to ignore parts of the git repo.
- New `--commit` cmd line arg, which just commits all pending changes with a sensible commit message geneated by gpt-3.5.
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
