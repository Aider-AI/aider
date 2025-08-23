# Chat Summarization Process

## Key Features

1. Hierarchy of Models:
   - Attempts cheaper models first
   - Falls back to stronger models

2. Token Management:
   - Triggers when history exceeds limit (default 1024)
   - Uses recursive summarization for long histories
   - Preserves recent messages intact when possible

3. Context Preservation:
   - Maintains file references
   - Keeps system messages
   - Retains key discussion points

## Implementation

- Managed by `ChatSummary` class
- Uses divide-and-conquer strategy
- Splits long histories recursively
- Maintains message alternation (user/assistant)
