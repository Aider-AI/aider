## Project Roadmap/Goals

The current priorities are to improve core capabilities and user experience of the Aider project

1. **Base Asynchronicity (aider-ce coroutine-experiment branch)**
  * [x] Refactor codebase to have the main loop run asynchronously
  * [x] Update test harness to work with new asynchronous methods

2. **Repo Map Accuracy** - [Discussion](https://github.com/dwash96/aider-ce/issues/45)
  * [x] [Bias page ranking toward active/editable files in repo map parsing](https://github.com/Aider-AI/aider/issues/2405)
  * [ ] [Include import information in repo map for richer context](https://github.com/Aider-AI/aider/issues/2688)  
  * [ ] [Handle non-unique symbols that break down in large codebases](https://github.com/Aider-AI/aider/issues/2341)

3. **Context Discovery** - [Discussion](https://github.com/dwash96/aider-ce/issues/46)
  * [ ] Develop AST-based search capabilities
  * [ ] Enhance file search with ripgrep integration
  * [ ] Implement RAG (Retrieval-Augmented Generation) for better code retrieval
  * [ ] Build an explicit workflow and local tooling for internal discovery mechanisms

4. **Context Delivery** - [Discussion](https://github.com/dwash96/aider-ce/issues/47)
  * [ ] Use workflow for internal discovery to better target file snippets needed for specific tasks
  * [ ] Add support for partial files and code snippets in model completion messages   

5. **TUI Experience** - [Discussion](https://github.com/dwash96/aider-ce/issues/48)
  * [ ] Add a full TUI (probably using textual) to have a visual interface competitive with the other coding agent terminal programs
  * [x] Re-integrate pretty output formatting
  * [ ] Implement a response area, a prompt area with current auto completion capabilities, and a helper area for management utility commands

6. **Agent Mode** - [Discussion](https://github.com/dwash96/aider-ce/issues/111)
  * [x] Renaming "navigator mode" to "agent mode" for simplicity
  * [x] Add an explicit "finished" internal tool
  * [x] Add a configuration json setting for agent mode to specify allowed local tools to use, tool call limits, etc.
  * [ ] Add a RAG tool for the model to ask questions about the codebase
  * [ ] Make the system prompts more aggressive about removing unneeded files/content from the context
  * [ ] Add a plugin-like system for allowing agent mode to use user-defined tools in simple python files
  * [ ] Add a dynamic tool discovery tool to allow the system to have only the tools it needs in context

### Documentation and Other Notes
* [Agent Mode](https://github.com/dwash96/aider-ce/blob/main/aider/website/docs/config/agent-mode.md)
* [MCP Configuration](https://github.com/dwash96/aider-ce/blob/main/aider/website/docs/config/mcp.md)
* [Session Management](https://github.com/dwash96/aider-ce/blob/main/aider/website/docs/sessions.md)
* [Aider Original Documentation (still mostly applies)](https://aider.chat/)
* [Discord Community](https://discord.gg/McwdCRuqkJ)

### Installation Instructions
This project can be installed using several methods:

### Package Installation
```bash
pip install aider-ce
```

or

```bash
uv pip install aider-ce
```

The package exports an `aider-ce` command that accepts all of Aider's configuration options

### Tool Installation
```bash
uv tool install --python python3.12 aider-ce
```

Use the tool installation so aider doesn't interfere with your development environment

### Merged PRs

* [MCP: #3937](https://github.com/Aider-AI/aider/pull/3937)
    * [MCP Multi Tool Response](https://github.com/quinlanjager/aider/pull/1)
* [Navigator Mode: #3781](https://github.com/Aider-AI/aider/pull/3781)
    * [Navigator Mode Large File Count](https://github.com/Aider-AI/aider/commit/b88a7bda649931798209945d9687718316c7427f)
    * [Fix navigator mode auto commit](https://github.com/dwash96/aider-ce/issues/38)
* [Qwen 3: #4383](https://github.com/Aider-AI/aider/pull/4383)
* [Fuzzy Search: #4366](https://github.com/Aider-AI/aider/pull/4366)
* [Map Cache Location Config: #2911](https://github.com/Aider-AI/aider/pull/2911)
* [Enhanced System Prompts: #3804](https://github.com/Aider-AI/aider/pull/3804)
* [Repo Map File Name Truncation Fix: #4320](https://github.com/Aider-AI/aider/pull/4320)
* [Read Only Stub Files For Context Window Management : #3056](https://github.com/Aider-AI/aider/pull/3056)

### Other Updates

* [Added Remote MCP Tool Calls With HTTP Streaming](https://github.com/Aider-AI/aider/commit/a86039f73579df7c32fee910967827c9fccdec0d)
    * [Enforce single tool call at a time](https://github.com/Aider-AI/aider/commit/3346c3e6194096cef64b1899b017bde36a65f794)
    * [Upgraded MCP dep to 1.12.3 for Remote MCP Tool Calls](https://github.com/dwash96/aider-ce/commit/a91ee1c03627a31093364fd2a09e654781b1b879)
    * [Updated base Python version to 3.12 to better support navigator mode (might consider undoing this, if dependency list supports it)](https://github.com/dwash96/aider-ce/commit/9ed416d523c11362a3ba9fc4c02134e0e79d41fc)
* [Suppress LiteLLM asyncio errors that clutter output](https://github.com/Aider-AI/aider/issues/6)
* [Updated Docker File Build Process](https://github.com/Aider-AI/aider/commit/cbab01458d0a35c03b30ac2f6347a74fc2b9f662)
    * [Manually install necessary ubuntu dependencies](https://github.com/dwash96/aider-ce/issues/14)
* [.gitignore updates](https://github.com/dwash96/aider-ce/commit/7c7e803fa63d1acd860eef1423e5a03220df6017)
* [Experimental Context Compaction For Longer Running Generation Tasks](https://github.com/Aider-AI/aider/issues/6)
* [Edit Before Adding Files and Reflecting](https://github.com/dwash96/aider-ce/pull/22)
* [Fix Deepseek model configurations](https://github.com/Aider-AI/aider/commit/c839a6dd8964d702172cae007375e299732d3823)
* [Relax Version Pinning For Easier Distribution](https://github.com/dwash96/aider-ce/issues/18)
* [Remove Confirm Responses from History](https://github.com/Aider-AI/aider/pull/3958)
* [Benchmark Results By Language](https://github.com/dwash96/aider-ce/pull/27)
* [Allow Benchmarks to Use Repo Map For Better Accuracy](https://github.com/dwash96/aider-ce/pull/25)
* [Read File Globbing](https://github.com/Aider-AI/aider/pull/3395)

### All Contributors (Both Aider Main and Aider-CE)

<a href="https://github.com/dwash96/aider-ce/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=dwash96/aider-ce" />
</a>

