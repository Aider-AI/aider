# Agent Mode

Agent Mode is an operational mode in aider-ce that enables autonomous codebase exploration and modification using local tools. Instead of relying on traditional edit formats, Agent Mode uses a tool-based approach where the LLM can discover, analyze, and modify files through a series of tool calls.

Agent Mode can be activated in the following ways

In the interface:

```
/agent
```

In the command line:

```
aider-ce ... --agent
```

In the configuration files:

```
agent: true
```

## How Agent Mode Works

### Core Architecture

Agent Mode operates through a continuous loop where the LLM:

1. **Receives a user request** and analyzes the current context
2. **Uses discovery tools** to find relevant files and information
3. **Executes editing tools** to make changes
4. **Processes results** and continues exploration and editing until the task is complete

This loop continues automatically until the `Finished` tool is called, or the maximum number of iterations is reached.

### Key Components

#### Tool Registry System

Agent Mode uses a centralized local tool registry that manages all available tools:

- **File Discovery Tools**: `View`, `ViewFilesMatching`, `ViewFilesWithSymbol`, `Ls`, `Grep`
- **Editing Tools**: `ReplaceText`, `InsertBlock`, `DeleteBlock`, `ReplaceLines`, `DeleteLines`
- **Context Management Tools**: `MakeEditable`, `MakeReadonly`, `Remove`
- **Git Tools**: `GitDiff`, `GitLog`, `GitShow`, `GitStatus`
- **Utility Tools**: `UpdateTodoList`, `ListChanges`, `UndoChange`, `Finished`

#### Enhanced Context Management

Agent Mode includes some useful context management features:

- **Automatic file tracking**: Files added during exploration are tracked separately
- **Context blocks**: Directory structure, git status, symbol outlines, and environment info
- **Token management**: Automatic calculation of context usage and warnings when approaching limits
- **Tool usage history**: Tracks repetitive tool usage to prevent exploration loops

### Key Features

#### Autonomous Context Management

- **Proactive file discovery**: LLM can find relevant files without user guidance
- **Smart file removal**: Large files can be removed from context to save tokens
- **Dynamic context updates**: Context blocks provide real-time project information

#### Granular Editing Capabilities

Agent Mode prioritizes granular tools over SEARCH/REPLACE:

- **Precision editing**: `ReplaceText` for targeted changes
- **Block operations**: `InsertBlock`, `DeleteBlock` for larger modifications
- **Line-based editing**: `ReplaceLines`, `DeleteLines` with safety protocols
- **Refactoring support**: `ExtractLines` for code reorganization

#### Safety and Recovery

- **Undo capability**: `UndoChange` tool for immediate recovery from mistakes
- **Dry run support**: Tools can be tested with `dry_run=True`
- **Line number verification**: Two-step process for line-based edits to prevents errors
- **Tool usage monitoring**: Prevents infinite loops by tracking repetitive patterns

### Workflow Process

#### 1. Exploration Phase

The LLM uses discovery tools to gather information:

```
Tool Call: ViewFilesMatching
Arguments: {"pattern": "config", "file_pattern": "*.py"}

Tool Call: View
Arguments: {"file_path": "main.py"}

Tool Call: Grep
Arguments: {"pattern": "function_name"}
```

Files found during exploration are added to context as read-only, allowing the LLM to analyze them without immediate editing.

#### 2. Planning Phase

The LLM uses the `UpdateTodoList` tool to track progress and plan complex changes:

```
Tool Call: UpdateTodoList
Arguments: {"content": "## Task: Add new feature\n- [ ] Analyze existing code\n- [ ] Implement new function\n- [ ] Add tests\n- [ ] Update documentation"}
```

#### 3. Execution Phase

Files are made editable and modifications are applied:

```
Tool Call: MakeEditable
Arguments: {"file_path": "main.py"}

Tool Call: ReplaceText
Arguments: {"file_path": "main.py", "find_text": "old_function", "replace_text": "new_function"}

Tool Call: InsertBlock
Arguments: {"file_path": "main.py", "after_pattern": "import statements", "content": "new_imports"}
```

#### 4. Verification Phase

Changes are verified and the process continues:

```
Tool Call: GitDiff
Arguments: {}

Tool Call: ListChanges
Arguments: {}
```

#### 5. Completion Phase

The above continues over and over until:

```
Tool Call: Finished
Arguments: {}
```

### Agent Configuration

Agent Mode can be configured using the `--agent-config` command line argument, which accepts a JSON string for fine-grained control over tool availability and behavior.

#### Configuration Options

- **`large_file_token_threshold`**: Maximum token threshold for large file warnings (default: 25000)
- **`skip_cli_confirmations`**: YOLO mode, be brave and let the LLM cook, can also use the option `yolo` (default: False)
- **`tools_includelist`**: Array of tool names to allow (only these tools will be available)
- **`tools_excludelist`**: Array of tool names to exclude (these tools will be disabled)

#### Essential Tools

Certain tools are always available regardless of includelist/excludelist settings:

- `makeeditable` - Make files editable
- `replacetext` - Basic text replacement
- `view` - View files
- `finished` - Complete the task

#### Usage Examples

```bash
# Only allow specific tools
aider-ce --agent --agent-config '{"tools_includelist": ["view", "makeeditable", "replacetext", "finished"]}'

# Exclude specific tools
aider-ce --agent --agent-config '{"tools_excludelist": ["command", "commandinteractive"]}'

# Custom large file threshold
aider-ce --agent --agent-config '{"large_file_token_threshold": 10000}'

# Combined configuration
aider-ce --agent --agent-config '{"large_file_token_threshold": 10000, "tools_includelist": ["view", "makeeditable", "replacetext", "finished", "gitdiff"]}'
```

This configuration system allows for fine-grained control over which tools are available in Agent Mode, enabling security-conscious deployments and specialized workflows while maintaining essential functionality.

### Benefits

- **Autonomous operation**: Reduces need for manual file management
- **Context awareness**: Real-time project information improves decision making
- **Precision editing**: Granular tools reduce errors compared to SEARCH/REPLACE
- **Scalable exploration**: Can handle large codebases through strategic context management
- **Recovery mechanisms**: Built-in undo and safety features

Agent Mode represents a significant evolution in aider's capabilities, enabling more sophisticated and autonomous codebase manipulation while maintaining safety and control through the tool-based architecture.

