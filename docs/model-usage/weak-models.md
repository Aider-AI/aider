# Weak Model Usage

## Key Scenarios

1. **Commit Message Generation**
   - First tries weak model to save costs/API limits
   - Falls back to main model if needed
   - Controlled by `commit_message_models()` method

2. **Chat History Summarization**
   - Uses weak model first for cost efficiency
   - Falls back to main model on failure
   - Reduces token usage while preserving context

## Implementation Details

- Configured via `weak_model` parameter in Model class
- Hierarchy defined in MODEL_SETTINGS
- Automatically falls back to main model if no weak model specified
- Used for non-critical tasks to preserve main model capacity
