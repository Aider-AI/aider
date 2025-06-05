---
nav_order: 30
has_children: true
description: How to use aider to pair program with AI and edit code in your local git repo.
---

# Usage

Run `aider` with the source code files you want to edit.
These files will be "added to the chat session", so that
aider can see their
contents and edit them for you.
They can be existing files or the name of files you want
aider to create for you.

```
aider <file1> <file2> ...
```

At the aider `>` prompt, ask for code changes and aider
will edit those files to accomplish your request.


```
$ aider factorial.py

Aider v0.37.1-dev
Models: gpt-4o with diff edit format, weak model gpt-3.5-turbo
Git repo: .git with 258 files
Repo-map: using 1024 tokens
Use /help to see in-chat commands, run with --help to see cmd line args
───────────────────────────────────────────────────────────────────────
> Make a program that asks for a number and prints its factorial

...
```

{% include help-tip.md %}

## Adding files

To edit files, you need to "add them to the chat".
Do this
by naming them on the aider command line.
Or, you can use the in-chat
`/add` command to add files.


Only add the files that need to be edited for your task.
Don't add a bunch of extra files.
If you add too many files, the LLM can get overwhelmed
and confused (and it costs more tokens).
Aider will automatically
pull in content from related files so that it can
[understand the rest of your code base](https://aider.chat/docs/repomap.html).

You can use aider without adding any files,
and it will try to figure out which files need to be edited based
on your requests.

{: .tip }
You'll get the best results if you think about which files need to be
edited. Add **just** those files to the chat. Aider will include
relevant context from the rest of your repo.

## LLMs

{% include works-best.md %}

```
# o3-mini
$ aider --model o3-mini --api-key openai=<key>

# Claude 3.7 Sonnet
$ aider --model sonnet --api-key anthropic=<key>
```

Or you can run `aider --model XXX` to launch aider with
another model.
During your chat you can switch models with the in-chat
`/model` command.

## Making changes

Ask aider to make changes to your code.
It will show you some diffs of the changes it is making to
complete you request.
[Aider will git commit all of its changes](/docs/git.html),
so they are easy to track and undo.

You can always use the `/undo` command to undo AI changes that you don't
like.

## `/voice` and `/novoice`

Use `/voice` to start an interactive voice transcription session using the default microphone.
Aider will capture your speech, transcribe it, and then submit the transcription as your input.
Use `/novoice` to end the voice transcription session.

You can configure the `voice-input-device` and other voice settings. See the output of `aider --help` for more details.

## Agent Mode

Aider includes an experimental **Agent Mode** designed for more autonomous task completion. When invoked, the agent will attempt to understand your task, create a plan, design tests, write code, and even debug issues with some level of independence.

### Invoking Agent Mode

You can start the agent by using the `/agent` command followed by your initial task description:

```
/agent <your detailed task description>
```
For example:
```
/agent Create a new Python script named 'utils.py' that includes a function to calculate factorial and write unit tests for it.
```

### Agent Phases

The agent operates through several distinct phases:

1.  **Clarification:** The agent will ask questions if your initial task is ambiguous. You'll interact with it to refine the requirements.
2.  **Planning:** Once the task is clear, the agent generates a step-by-step plan consisting of smaller deliverables.
3.  **Test Design:** For each deliverable and the overall plan, the agent will propose unit and integration tests, respectively. It will also try to suggest an appropriate command to run these tests.
4.  **Approval (Optional):** By default, the agent will present its plan, test designs, and suggested test command for your approval. You can type `yes` to proceed, `no` to stop the agent, or `modify` to pause the agent and provide new instructions or edits.
5.  **Execution:** The agent works through each deliverable. This involves:
    *   Potentially performing repository searches (for existing relevant code) and web searches (for implementation guidance or error resolution).
    *   Writing or modifying code.
    *   Running unit tests for the current deliverable. If tests fail, it enters a debugging loop, attempting to fix the issues with LLM assistance and further web/repo searches.
6.  **Integration Testing:** After all deliverables are attempted, the agent runs integration tests. If these fail, a similar debugging loop is initiated.
7.  **Reporting:** Finally, the agent provides a summary of the work it performed.

After the agent completes its task (or is stopped), it will typically switch back to Aider's standard interaction mode.

### Configuring Agent Behavior

Several command-line arguments can influence the agent's operation:

*   `--agent-auto-approve`: If you start `aider` with this flag, the agent will bypass the manual **Approval** phase and automatically proceed with its generated plan and tests.
    ```bash
    aider --agent-auto-approve
    ```
*   `--agent-web-search {always|on_demand|never}`: This flag controls the agent's web search behavior:
    *   `always`: The agent will automatically perform web searches at relevant points (clarification, planning, coding, debugging).
    *   `on_demand`: The agent will ask for your permission before performing each web search (this is useful for controlling costs or focusing the search).
    *   `never` (default): The agent will not perform any web searches.
    ```bash
    aider --agent-web-search on_demand
    ```
*   `--agent-headless`: For programmatic or fully unattended execution. When this flag is set:
    *   The interactive **Clarification** phase is skipped. The agent uses the initial task description directly.
    *   It implies `--agent-auto-approve`, so the **Approval** phase is also skipped.
    *   If `--agent-web-search` was set to `on_demand`, it will be defaulted to `never` to prevent blocking for user input.
    *   LLM communication errors will attempt one automatic retry without prompting.
    ```bash
    aider --agent-headless --message "Refactor utils.py to improve readability."
    ```
*   **Test Execution Command:** The agent will attempt to suggest a command to run tests (e.g., `python -m unittest discover`, `pytest`).

Agent mode is a powerful feature. Monitor its progress, especially during its initial uses, to understand its workflow and ensure it aligns with your expectations.

### Agent Mode Flags

*   `--agent-web-search {always|on_demand|never}`: Control when the agent can perform web searches. Defaults to `on_demand`.
*   `--agent-auto-approve`: If set, the agent will automatically approve its generated plan and test strategy, skipping the manual approval phase. Useful for faster iterations or headless mode.
*   `--agent-headless`: Runs the agent in a non-interactive mode. Implies `--agent-auto-approve`. Web search defaults to `never` if it was `on_demand`. The agent starts directly with the planning phase using the initial task.

### Advanced: Hierarchical Planning and Test Generation

Aider Agent can optionally employ a more sophisticated hierarchical planning approach and generate different levels of test detail. This allows for breaking down complex tasks into major deliverables, and then further into atomic sub-tasks, with tests defined at each appropriate level.

*   `--agent-hierarchical-planning {none|deliverables_only|full_two_level}`:
    *   `none` (default): The agent generates a flat list of deliverables.
    *   `deliverables_only`: The agent generates a list of major deliverables. For planning and execution, these are treated as the primary tasks. (Currently, its behavior in execution and test design closely mirrors `none`, but it sets the stage for future distinct handling if needed).
    *   `full_two_level`: The agent first generates major deliverables. Then, for each major deliverable, it attempts to decompose it into smaller, atomic sub-tasks. Execution will proceed through sub-tasks first, followed by integration tests for the major deliverable.

*   `--agent-generate-tests {none|descriptions|all_code}`:
    *   `none` (default): The agent does not attempt to generate specific tests for its planned deliverables. It will still try to determine a general test command for the project.
    *   `descriptions`: The agent will generate textual descriptions of unit tests (for atomic tasks/sub-tasks) and integration tests (for non-atomic major deliverables and the overall request). These descriptions guide the LLM during coding and debugging.
    *   `all_code`: The agent will attempt to generate actual, runnable code snippets for unit and integration tests. These are stored in the plan. Note: Currently, the agent primarily uses a single configured project-level test command (e.g., `pytest`) to validate changes. The generated test code serves as a highly specific guide for the LLM and for future enhancements where these specific test snippets might be executed directly.

**How it Works with Hierarchical Planning:**

When `full_two_level` hierarchical planning is active:
1.  **Planning Phase:** The agent creates a plan (`self.plan`) containing `major_deliverables`. Each major deliverable can either be marked `is_atomic: true` or have a list of `atomic_sub_tasks`.
2.  **Test Design Phase:** Based on the `--agent-generate-tests` setting:
    *   Unit tests are generated for each atomic sub-task (if any) and for major deliverables that are atomic.
    *   Integration tests are generated for non-atomic major deliverables (to test the integration of their sub-tasks).
    *   Overall integration tests are generated for the entire user request.
    *   These tests (descriptions or code) are stored within the `self.plan` structure, associated with their respective tasks.
3.  **Execution Phase:**
    *   The agent iterates through major deliverables.
    *   For non-atomic major deliverables, it first executes each atomic sub-task (including coding, applying edits, and running its unit tests with a debugging loop).
    *   If all sub-tasks of a non-atomic major deliverable are completed, its specific integration tests are then (conceptually) run. Failures here would ideally trigger a debugging loop for the major deliverable (this debugging part is a current TODO for refinement).
    *   For atomic major deliverables, they are executed directly (code, edit, test, debug).
4.  **Reporting Phase:** The final report will summarize the outcomes (this phase also needs an update to reflect the hierarchical structure).

This advanced planning and test generation can be very powerful for complex tasks, providing better structure and more targeted verification steps. However, it also relies more heavily on the LLM's capabilities for decomposition and test creation.

## Voice Input

Use `/voice` to start an interactive voice transcription session using the default microphone.
Aider will capture your speech, transcribe it, and then submit the transcription as your input.
Use `/novoice` to end the voice transcription session.

You can configure the `voice-input-device` and other voice settings. See the output of `aider --help` for more details.
