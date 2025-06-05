---
nav_order: 35
has_children: true
title: "AgentCoder Usage"
description: "Comprehensive guide for using AgentCoder in both terminal and programmatic modes"
---

# AgentCoder Usage Guide

AgentCoder is an autonomous AI agent built into Aider that can break down complex tasks into manageable sub-tasks, generate comprehensive test strategies, and execute implementations with minimal human intervention. This guide covers both terminal and programmatic usage.

## Overview

AgentCoder operates through several distinct phases:

1. **Clarification Phase**: Interactive task refinement (skipped in headless mode)
2. **Planning Phase**: Hierarchical task decomposition and planning
3. **Test Design Phase**: Generation of unit and integration tests
4. **Approval Phase**: User review and approval (skipped with auto-approve)
5. **Execution Phase**: Implementation of planned tasks
6. **Integration Testing Phase**: Running and debugging overall tests
7. **Reporting Phase**: Summary of completed work

## Terminal Usage

### Basic Invocation

#### Using the `/agent` Command

From within an active Aider session:

```bash
/agent Create a REST API for user management with CRUD operations
```

#### Using Command Line Arguments

Start Aider directly in agent mode:

```bash
# Basic agent mode
aider --agent-coder --message "Create a REST API for user management"

# With specific configuration
aider --agent-coder \
      --agent-hierarchical-planning full_two_level \
      --agent-generate-tests all_code \
      --agent-max-decomposition-depth 3 \
      --message "Build a complete web application with authentication"
```

### Configuration Options

#### Core Agent Settings

- `--agent-coder`: Enable AgentCoder mode
- `--agent-auto-approve`: Skip manual approval phase
- `--agent-headless`: Run without interactive prompts (implies auto-approve)

#### Planning Configuration

- `--agent-hierarchical-planning {none|deliverables_only|full_two_level}`:
  - `none`: Flat task list (default)
  - `deliverables_only`: Plan major deliverables only
  - `full_two_level`: Full hierarchical decomposition

- `--agent-max-decomposition-depth N`: Maximum depth for task decomposition (default: 2)

#### Test Generation

- `--agent-generate-tests {none|descriptions|all_code}`:
  - `none`: No test generation (default)
  - `descriptions`: Generate test descriptions
  - `all_code`: Generate executable test code

#### Advanced Features

- `--agent-enable-planner-executor-arch`: Use separate models for planning and execution
- `--agent-planner-model MODEL`: Specify model for planning tasks
- `--agent-executor-model MODEL`: Specify model for code execution
- `--agent-output-plan-only`: Generate plan and exit without execution
- `--agent-web-search {always|on_demand|never}`: Control web search behavior

### Example Workflows

#### Simple Task Execution

```bash
# Interactive mode with clarification
aider --agent-coder
# Then use: /agent Implement a calculator class with basic operations

# Headless mode for automation
aider --agent-coder --agent-headless \
      --message "Create a Python module for file processing utilities"
```

#### Complex Project with Full Planning

```bash
aider --agent-coder \
      --agent-hierarchical-planning full_two_level \
      --agent-generate-tests all_code \
      --agent-max-decomposition-depth 4 \
      --agent-auto-approve \
      --message "Build a complete e-commerce API with user auth, product catalog, and order management"
```

#### Plan-Only Mode for Review

```bash
aider --agent-coder \
      --agent-output-plan-only \
      --agent-hierarchical-planning full_two_level \
      --agent-generate-tests descriptions \
      --message "Design a microservices architecture for a social media platform"
```

#### Multi-Model Architecture

```bash
aider --agent-coder \
      --agent-enable-planner-executor-arch \
      --agent-planner-model "gpt-4" \
      --agent-executor-model "claude-3-5-sonnet-20241022" \
      --agent-hierarchical-planning full_two_level \
      --message "Implement a distributed caching system"
```

## Programmatic Usage

### Basic Setup

```python
import sys
import os
from aider.coders.agent_coder import AgentCoder
from aider.models import Model
from aider.io import InputOutput

# Initialize components
io = InputOutput(pretty=True, yes=True, encoding="utf-8")
main_model = Model("gpt-4")

# Define your task
task = "Create a Python web scraper with rate limiting and error handling"

# Create AgentCoder instance
agent = AgentCoder(
    main_model=main_model,
    io=io,
    repo=None,  # Or pass a GitRepo instance
    from_coder=None,
    initial_task=task,
    stream=False,  # Disable streaming for programmatic use
    args=None  # Or pass an args object with configuration
)

# Execute the agent
try:
    agent.run()
    print("Agent execution completed successfully")
except Exception as e:
    print(f"Agent execution failed: {e}")
```

### Advanced Configuration with Args Object

```python
from aider.coders.agent_coder import AgentCoder
from aider.models import Model
from aider.io import InputOutput

class AgentArgs:
    def __init__(self):
        # Core settings
        self.agent_hierarchical_planning = 'full_two_level'
        self.agent_generate_tests = 'all_code'
        self.agent_max_decomposition_depth = 3
        self.agent_headless = True
        self.agent_auto_approve = True
        self.agent_web_search = "never"
        
        # Advanced features
        self.agent_enable_planner_executor_arch = False
        self.agent_planner_model = None
        self.agent_executor_model = None
        self.agent_output_plan_only = False

def create_agent_with_config(task, model_name="gpt-4"):
    io = InputOutput(pretty=True, yes=True, encoding="utf-8")
    main_model = Model(model_name)
    args = AgentArgs()
    
    agent = AgentCoder(
        main_model=main_model,
        io=io,
        repo=None,
        from_coder=None,
        initial_task=task,
        stream=False,
        args=args
    )
    
    return agent

# Usage
task = "Build a complete REST API with authentication, CRUD operations, and comprehensive testing"
agent = create_agent_with_config(task, "claude-3-5-sonnet-20241022")

try:
    agent.run()
    
    # Access results
    if agent.plan:
        print("Generated Plan:")
        import json
        print(json.dumps(agent.plan, indent=2, default=str))
    
    if agent.agent_test_command:
        print(f"Suggested test command: {agent.agent_test_command}")
        
    print(f"Files modified: {list(agent.agent_touched_files_rel)}")
    print(f"Integration test status: {agent.integration_tests_final_status}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

### Plan-Only Mode for Analysis

```python
from aider.coders.agent_coder import AgentCoder
from aider.models import Model
from aider.io import InputOutput
import json

class PlanOnlyArgs:
    def __init__(self):
        self.agent_hierarchical_planning = 'full_two_level'
        self.agent_generate_tests = 'descriptions'
        self.agent_max_decomposition_depth = 4
        self.agent_output_plan_only = True  # Key setting
        self.agent_headless = True
        self.agent_auto_approve = True
        self.agent_web_search = "never"
        self.agent_enable_planner_executor_arch = False
        self.agent_planner_model = None
        self.agent_executor_model = None

def analyze_task_complexity(task, model_name="gpt-4"):
    """Generate a detailed plan without executing it"""
    io = InputOutput(pretty=True, yes=True, encoding="utf-8")
    main_model = Model(model_name)
    args = PlanOnlyArgs()
    
    agent = AgentCoder(
        main_model=main_model,
        io=io,
        repo=None,
        from_coder=None,
        initial_task=task,
        stream=False,
        args=args
    )
    
    # Capture stdout to get the JSON plan
    import io as string_io
    import sys
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = string_io.StringIO()
    
    try:
        agent.run()
        plan_json = captured_output.getvalue()
        return json.loads(plan_json)
    finally:
        sys.stdout = old_stdout

# Usage
task = "Design and implement a distributed microservices architecture"
plan = analyze_task_complexity(task)

print("Task Analysis Results:")
print(f"Initial task: {plan['initial_task']}")
print(f"Clarified task: {plan['clarified_task']}")
print(f"Number of major deliverables: {len(plan['plan']['tasks'])}")
print(f"Suggested test command: {plan['suggested_test_command']}")

for i, task_item in enumerate(plan['plan']['tasks'], 1):
    print(f"\nDeliverable {i}: {task_item['description']}")
    if task_item.get('sub_tasks'):
        print(f"  Sub-tasks: {len(task_item['sub_tasks'])}")
    if task_item.get('unit_tests'):
        print(f"  Unit tests: {len(task_item['unit_tests'])}")
```

### Multi-Model Architecture

```python
from aider.coders.agent_coder import AgentCoder
from aider.models import Model
from aider.io import InputOutput

class MultiModelArgs:
    def __init__(self):
        self.agent_hierarchical_planning = 'full_two_level'
        self.agent_generate_tests = 'all_code'
        self.agent_max_decomposition_depth = 3
        self.agent_headless = True
        self.agent_auto_approve = True
        self.agent_web_search = "never"
        
        # Multi-model configuration
        self.agent_enable_planner_executor_arch = True
        self.agent_planner_model = "gpt-4"  # Good for planning and analysis
        self.agent_executor_model = "claude-3-5-sonnet-20241022"  # Good for code generation
        self.agent_output_plan_only = False

def create_multi_model_agent(task):
    io = InputOutput(pretty=True, yes=True, encoding="utf-8")
    main_model = Model("gpt-4")  # Fallback model
    args = MultiModelArgs()
    
    agent = AgentCoder(
        main_model=main_model,
        io=io,
        repo=None,
        from_coder=None,
        initial_task=task,
        stream=False,
        args=args
    )
    
    return agent

# Usage
task = "Create a high-performance web API with caching, monitoring, and comprehensive test suite"
agent = create_multi_model_agent(task)

try:
    agent.run()
    print("Multi-model agent execution completed")
except Exception as e:
    print(f"Error: {e}")
```

### Integration with Existing Codebase

```python
from aider.coders.agent_coder import AgentCoder
from aider.models import Model
from aider.io import InputOutput
from aider.repo import GitRepo
from pathlib import Path

def enhance_existing_project(task, project_path, files_to_include=None):
    """Run AgentCoder on an existing project"""
    
    # Initialize with existing repository
    io = InputOutput(pretty=True, yes=True, encoding="utf-8")
    main_model = Model("claude-3-5-sonnet-20241022")
    
    # Set up repository
    repo = GitRepo(io, files_to_include or [], str(project_path))
    
    class ProjectArgs:
        def __init__(self):
            self.agent_hierarchical_planning = 'deliverables_only'
            self.agent_generate_tests = 'all_code'
            self.agent_max_decomposition_depth = 2
            self.agent_headless = True
            self.agent_auto_approve = True
            self.agent_web_search = "never"
            self.agent_enable_planner_executor_arch = False
            self.agent_planner_model = None
            self.agent_executor_model = None
            self.agent_output_plan_only = False
    
    args = ProjectArgs()
    
    agent = AgentCoder(
        main_model=main_model,
        io=io,
        repo=repo,
        from_coder=None,
        initial_task=task,
        stream=False,
        args=args,
        fnames=files_to_include or []
    )
    
    return agent

# Usage
project_path = Path("./my-existing-project")
files_to_modify = ["src/main.py", "src/utils.py"]
task = "Add comprehensive error handling and logging to the existing codebase"

agent = enhance_existing_project(task, project_path, files_to_modify)

try:
    agent.run()
    print(f"Enhanced project at {project_path}")
    print(f"Modified files: {list(agent.agent_touched_files_rel)}")
except Exception as e:
    print(f"Enhancement failed: {e}")
```

## Best Practices

### Task Description Guidelines

1. **Be Specific**: Provide clear, detailed requirements
   ```bash
   # Good
   /agent Create a REST API with user authentication using JWT, CRUD operations for posts, rate limiting, and comprehensive error handling
   
   # Less effective
   /agent Make a web API
   ```

2. **Include Context**: Mention technologies, constraints, and requirements
   ```bash
   /agent Build a Python Flask API with SQLAlchemy ORM, Redis caching, and pytest test suite
   ```

3. **Specify Quality Requirements**: Include testing, documentation, and performance needs
   ```bash
   /agent Implement a file processing system with 95% test coverage, comprehensive error handling, and performance monitoring
   ```

### Configuration Recommendations

#### For Simple Tasks
```bash
aider --agent-coder --agent-auto-approve
```

#### For Complex Projects
```bash
aider --agent-coder \
      --agent-hierarchical-planning full_two_level \
      --agent-generate-tests all_code \
      --agent-max-decomposition-depth 3
```

#### For Production Use
```bash
aider --agent-coder \
      --agent-hierarchical-planning full_two_level \
      --agent-generate-tests all_code \
      --agent-enable-planner-executor-arch \
      --agent-planner-model "gpt-4" \
      --agent-executor-model "claude-3-5-sonnet-20241022"
```

### Error Handling and Debugging

#### Common Issues and Solutions

1. **Task Too Complex**: Reduce decomposition depth or break into smaller tasks
2. **Test Failures**: Review generated tests and adjust implementation
3. **Model Limitations**: Use multi-model architecture for better results
4. **Integration Issues**: Enable verbose mode for detailed debugging

#### Debugging Options

```python
# Enable verbose output
io = InputOutput(pretty=True, yes=True, encoding="utf-8", verbose=True)

# Access detailed execution information
agent.verbose = True
agent.run()

# Review execution phases
print(f"Current phase: {agent.current_phase}")
print(f"Completed deliverables: {agent.completed_deliverables}")
print(f"Failed deliverables: {agent.failed_deliverables}")
```

## Output and Results

### Plan Structure

AgentCoder generates a hierarchical plan with the following structure:

```json
{
  "initial_task": "Original task description",
  "clarified_task": "Refined task after clarification",
  "plan": {
    "root_task_description": "Main task description",
    "tasks": [
      {
        "id": "md1",
        "description": "Major deliverable description",
        "is_atomic": false,
        "sub_tasks": [
          {
            "id": "md1_st1",
            "description": "Sub-task description",
            "is_atomic": true,
            "unit_tests": ["Test description 1", "Test description 2"]
          }
        ],
        "integration_tests": ["Integration test description"]
      }
    ],
    "overall_integration_tests": ["Overall system test description"]
  },
  "suggested_test_command": "pytest tests/"
}
```

### Execution Results

After execution, you can access:

- `agent.plan`: The generated plan structure
- `agent.agent_touched_files_rel`: Set of modified files
- `agent.completed_deliverables`: List of successfully completed tasks
- `agent.failed_deliverables`: List of failed tasks
- `agent.integration_tests_final_status`: Overall test status
- `agent.agent_test_command`: Suggested test command

## Limitations and Considerations

1. **Model Capabilities**: Results depend on the chosen LLM's capabilities
2. **Task Complexity**: Very complex tasks may require manual intervention
3. **Code Quality**: Generated code should be reviewed before production use
4. **Test Coverage**: Generated tests may not cover all edge cases
5. **Resource Usage**: Complex tasks consume significant API tokens

## Troubleshooting

### Common Error Messages

- **"Task too complex for automatic decomposition"**: Reduce max depth or simplify task
- **"No valid edit format found"**: Ensure model supports required edit format
- **"Integration tests failed"**: Review test output and adjust implementation
- **"Context window exceeded"**: Break task into smaller parts or use a model with larger context

### Performance Optimization

1. Use appropriate decomposition depth for task complexity
2. Enable caching for repeated operations
3. Use multi-model architecture for optimal performance
4. Consider plan-only mode for initial analysis

This comprehensive guide should help you effectively use AgentCoder for both simple automation tasks and complex software development projects. 