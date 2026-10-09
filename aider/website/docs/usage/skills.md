---
parent: Usage
nav_order: 65
description: Let Aider select project-specific skills for each request.
---

# Project skills

Project skills give Aider detailed instructions for particular kinds of work. Aider reads each skill's short description when choosing which skills fit a request, and includes the full instructions only for skills it selects.

## Create a skill

Add a `SKILL.md` file under `.agents/skills/<directory>/SKILL.md` in your project. The file starts with YAML frontmatter containing non-empty `name` and `description` fields, followed by the Markdown instructions:

```markdown
---
name: Test author
description: Write focused tests for code changes.
---

Add tests that cover the behavior and its edge cases.
```

The skill directory name is its stable identifier in Aider's catalog. The frontmatter `name` is the display name, and `description` is the concise summary used for automatic selection. You can create, edit, and remove these files outside Aider; Aider refreshes the catalog at the start of each top-level request.

## Automatic selection

For requests in `code`, `ask`, or `architect` mode, Aider automatically sends the retained conversation, the new request, and every valid skill's identifier, name, and description to the configured main model. It asks the model to return the identifiers that apply. Skill bodies are not included in this selection call. If skills are selected, Aider adds their complete instructions to the response prompt and prints their names.

Selection is temporary for that request. The same selected skills stay available during reflection or retries and pass from the architect model to the editor. The next top-level request makes a fresh selection. Skill instructions are not saved in conversation history.

Selection requires an additional model call whenever the project has at least one valid skill, even when no skill applies. This adds latency and cost. Aider includes selector and response tokens and cost in its normal usage report; selected skill instructions also count as prompt tokens when sent with a response.

## Invalid skills and selection failures

Aider prints a warning and skips a skill with malformed or missing metadata, or one whose file cannot be read. If the selection call fails, returns malformed data, or names an unknown identifier, Aider warns, loads no skill instructions, and uses the normal request path as a fallback.
