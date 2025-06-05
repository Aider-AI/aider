---
nav_order: 1
parent: "AgentCoder Usage"
title: "Architecture"
description: "Technical overview of AgentCoder's internal architecture and design patterns"
---

# AgentCoder Architecture

This document provides a technical overview of AgentCoder's internal architecture, design patterns, and implementation details.

## Core Architecture

### Class Hierarchy

```
Coder (base_coder.py)
└── AgentCoder (agent_coder.py)
    ├── Inherits all base functionality
    ├── Adds autonomous planning capabilities
    ├── Implements hierarchical task decomposition
    └── Delegates atomic tasks to existing coders
```

### Key Design Principles

1. **Delegation over Reimplementation**: AgentCoder delegates atomic task execution to proven existing coders (EditBlockCoder, etc.) rather than reimplementing edit parsing logic.

2. **Phase-Based Execution**: Clear separation of concerns through distinct execution phases.

3. **Hierarchical Planning**: Recursive task decomposition with configurable depth limits.

4. **Model Flexibility**: Support for single-model or multi-model architectures.

## Execution Phases

### 1. Clarification Phase (`run_clarification_phase`)

**Purpose**: Interactive refinement of the initial task description.

**Key Components**:
- `_clarify_task_with_user()`: Interactive task refinement
- `_get_llm_response()`: LLM communication with JSON parsing
- Clarification history tracking

**Flow**:
```
Initial Task → LLM Analysis → User Interaction → Refined Task
```

**Configuration**:
- Skipped when `agent_headless=True`
- Controlled by `agent_clarify_task` setting

### 2. Planning Phase (`run_planning_phase`)

**Purpose**: Hierarchical decomposition of tasks and generation of execution plan.

**Key Components**:
- `_decompose_task_recursively()`: Recursive task breakdown
- `_generate_plan_from_clarified_task()`: Plan generation
- Hierarchical planning modes: `none`, `deliverables_only`, `full_two_level`

**Flow**:
```
Clarified Task → Decomposition → Plan Generation → Validation
```

**Data Structures**:
```python
plan = {
    "root_task_description": str,
    "tasks": [
        {
            "id": str,
            "description": str,
            "is_atomic": bool,
            "sub_tasks": [...],  # Recursive structure
            "unit_tests": [str],
            "integration_tests": [str]
        }
    ],
    "overall_integration_tests": [str]
}
```

### 3. Test Design Phase (`run_test_design_phase`)

**Purpose**: Generation of comprehensive test strategies.

**Key Components**:
- `_generate_unit_tests_for_deliverable()`: Unit test generation
- `_generate_integration_tests_for_deliverable()`: Integration test generation
- `_generate_overall_integration_tests()`: System-level test generation
- `_propose_test_command()`: Test execution command suggestion

**Test Generation Modes**:
- `none`: No test generation
- `descriptions`: Generate test descriptions only
- `all_code`: Generate executable test code

### 4. Approval Phase (`run_approval_phase`)

**Purpose**: User review and approval of generated plan.

**Key Components**:
- Plan display and formatting
- Interactive approval workflow
- Plan modification support

**Configuration**:
- Skipped when `agent_auto_approve=True`
- Automatic in headless mode

### 5. Execution Phase (`run_execution_phase`)

**Purpose**: Implementation of planned tasks through delegation.

**Key Components**:
- `_execute_task_recursively()`: Recursive task execution
- `_execute_atomic_task()`: Atomic task delegation
- `_delegate_to_coder()`: Delegation to existing coders

**Delegation Architecture**:
```python
def _delegate_to_coder(self, task_message, use_executor_model=True):
    # Create temporary EditBlockCoder instance
    delegated_coder = EditBlockCoder(
        main_model=chosen_model,
        io=self.io,
        repo=self.repo,
        fnames=list(self.abs_fnames),
        # ... other context
    )
    
    # Execute task through proven coder infrastructure
    delegated_coder.run(with_message=task_message)
    
    # Track results
    return success_status
```

### 6. Integration Testing Phase (`run_integration_testing_phase`)

**Purpose**: Execution and validation of integration tests.

**Key Components**:
- Test execution with retry logic
- Error analysis and debugging
- Test result reporting

### 7. Reporting Phase (`run_reporting_phase`)

**Purpose**: Summary of completed work and results.

**Key Components**:
- Execution summary generation
- File modification tracking
- Success/failure reporting

## Core Methods and APIs

### LLM Communication

```python
def _get_llm_response(self, messages, expecting_json=False, model_role="planner"):
    """
    Centralized LLM communication with:
    - Model selection (planner vs executor)
    - JSON parsing and validation
    - Retry logic for malformed responses
    - Gemini compatibility (user message injection)
    """
```

### Task Decomposition

```python
def _decompose_task_recursively(self, task_description, current_depth=0, max_depth=None):
    """
    Recursive task breakdown with:
    - Depth limiting
    - Atomic task detection
    - JSON response parsing
    - Error handling
    """
```

### Delegation System

```python
def _delegate_to_coder(self, task_message, use_executor_model=True):
    """
    Task delegation to existing coders:
    - Model selection
    - Context preservation
    - Result tracking
    - Error handling
    """
```

## Configuration System

### Args Integration

AgentCoder integrates with Aider's argument system through the `args` parameter:

```python
class AgentCoder(Coder):
    def __init__(self, ..., args=None, ...):
        # Extract agent-specific configuration
        if args:
            self.agent_hierarchical_planning = getattr(args, 'agent_hierarchical_planning', 'none')
            self.agent_generate_tests = getattr(args, 'agent_generate_tests', 'none')
            # ... other settings
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `agent_hierarchical_planning` | str | 'none' | Planning mode |
| `agent_generate_tests` | str | 'none' | Test generation mode |
| `agent_max_decomposition_depth` | int | 2 | Maximum decomposition depth |
| `agent_headless` | bool | False | Run without interaction |
| `agent_auto_approve` | bool | False | Skip approval phase |
| `agent_enable_planner_executor_arch` | bool | False | Use separate models |
| `agent_planner_model` | str | None | Model for planning |
| `agent_executor_model` | str | None | Model for execution |
| `agent_output_plan_only` | bool | False | Generate plan only |
| `agent_web_search` | str | 'never' | Web search behavior |

## Model Architecture

### Single Model Mode

Default mode using one model for all operations:

```python
main_model = Model("claude-3-5-sonnet-20241022")
agent = AgentCoder(main_model=main_model, ...)
```

### Multi-Model Architecture

Separate models for planning and execution:

```python
# Configuration
args.agent_enable_planner_executor_arch = True
args.agent_planner_model = "gpt-4"  # Good for analysis
args.agent_executor_model = "claude-3-5-sonnet-20241022"  # Good for code

# Model selection logic
if model_role == "planner" and self.planner_llm:
    active_model = self.planner_llm
elif model_role == "executor" and self.executor_llm:
    active_model = self.executor_llm
else:
    active_model = self.main_model
```

## Data Flow

### High-Level Flow

```
User Input → Clarification → Planning → Test Design → Approval → Execution → Testing → Reporting
```

### Detailed Data Flow

```
1. Initial Task (string)
   ↓
2. Clarified Task (string)
   ↓
3. Task Decomposition (hierarchical JSON)
   ↓
4. Execution Plan (structured JSON)
   ↓
5. Test Strategy (test descriptions/code)
   ↓
6. User Approval (boolean)
   ↓
7. Task Execution (delegated to coders)
   ↓
8. Integration Testing (test results)
   ↓
9. Final Report (summary)
```

## Error Handling and Recovery

### LLM Response Parsing

```python
def _get_llm_response(self, messages, expecting_json=False, ...):
    for attempt in range(max_attempts):
        try:
            response = self.send(messages, model=active_model)
            if expecting_json:
                # Strip markdown fences
                if response.startswith("```json"):
                    response = response[7:]
                if response.endswith("```"):
                    response = response[:-3]
                
                parsed = json.loads(response.strip())
                # Validate against expected format
                return parsed
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt < max_attempts - 1:
                continue
            raise
```

### Task Execution Recovery

```python
def _execute_task_recursively(self, task, parent_description=None):
    try:
        if task.get("is_atomic"):
            return self._execute_atomic_task(task, parent_description)
        else:
            # Execute sub-tasks with error isolation
            results = []
            for sub_task in task.get("sub_tasks", []):
                try:
                    result = self._execute_task_recursively(sub_task, task["description"])
                    results.append(result)
                except Exception as e:
                    self.io.tool_error(f"Sub-task failed: {e}")
                    results.append(False)
            return any(results)  # Partial success allowed
    except Exception as e:
        self.io.tool_error(f"Task execution failed: {e}")
        return False
```

## Integration with Existing Aider Infrastructure

### Coder Delegation

AgentCoder leverages existing coder infrastructure:

```python
# Uses proven EditBlockCoder for actual implementation
from aider.coders.editblock_coder import EditBlockCoder

delegated_coder = EditBlockCoder(
    main_model=model,
    io=self.io,
    repo=self.repo,
    fnames=list(self.abs_fnames),
    # Inherit all context from AgentCoder
)

# Execute through established coder.run() interface
delegated_coder.run(with_message=task_message)
```

### Repository Integration

```python
# Full integration with GitRepo
if self.repo:
    # Automatic file tracking
    # Git operations
    # Commit management
    # .aiderignore/.gitignore respect
```

### IO System Integration

```python
# Uses existing InputOutput system
self.io.tool_output("Agent status message")
self.io.tool_error("Error message")
self.io.confirm_ask("User confirmation")
```

## Performance Considerations

### Token Usage Optimization

1. **Hierarchical Planning**: Reduces context size for individual tasks
2. **Delegation**: Reuses existing optimized prompts
3. **Caching**: Leverages model caching where available
4. **Depth Limiting**: Prevents excessive decomposition

### Memory Management

1. **Stateless Delegation**: Temporary coder instances are garbage collected
2. **Context Preservation**: Only essential context passed to delegated coders
3. **Result Tracking**: Minimal state retention for reporting

### Scalability

1. **Recursive Architecture**: Handles arbitrarily complex task hierarchies
2. **Error Isolation**: Failed sub-tasks don't break entire execution
3. **Partial Success**: Allows completion of successful tasks even with some failures

## Extension Points

### Custom Prompts

AgentCoder uses prompts from `aider/prompts.py`:

```python
# Planning prompts
agent_recursive_decompose_task_system
agent_planning_system

# Test generation prompts
agent_generate_unit_tests_system
agent_generate_integration_tests_for_major_deliverable_system

# Execution prompts
agent_coding_system
agent_debugging_system
```

### Custom Delegation Strategies

```python
def _delegate_to_coder(self, task_message, use_executor_model=True):
    # Override this method to use different coder types
    # or implement custom delegation logic
    pass
```

### Custom Validation

```python
def _validate_plan(self, plan):
    # Add custom plan validation logic
    pass

def _validate_test_strategy(self, tests):
    # Add custom test validation logic
    pass
```

## Testing and Debugging

### Debug Output

Enable verbose debugging:

```python
agent.verbose = True
# Or
io = InputOutput(verbose=True)
```

### Phase Tracking

```python
print(f"Current phase: {agent.current_phase}")
print(f"Completed deliverables: {agent.completed_deliverables}")
print(f"Failed deliverables: {agent.failed_deliverables}")
```

### Plan Inspection

```python
import json
print(json.dumps(agent.plan, indent=2, default=str))
```

This architecture enables AgentCoder to provide autonomous software development capabilities while leveraging Aider's proven infrastructure for reliable code generation and modification. 