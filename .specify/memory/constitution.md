# Project Constitution

## Core Principles

### SpecKit Compatibility
- Maintain compatibility with GitHub Spec Kit artifact model (constitution.md, spec.md, plan.md, tasks.md)
- Keep SpecKit artifact handling separate from MTARP execution state
- Treat Spec Kit artifacts as input intent; treat MTARP as execution state

### Implementation Philosophy
- Do not copy large parts of GitHub Spec Kit - build minimal compatible workflow
- Implement read-only artifact discovery before generation or implementation
- All initial functionality must work offline without calling an LLM
- MTARP snapshots must be deterministic YAML or JSON

### Code Quality
- Preserve compatibility with upstream aider where possible
- Prefer small, testable modules
- Use existing aider conventions, libraries, and patterns
- Follow aider's existing command structure and error handling patterns

### Development Constraints
- Keep SpecKit integration separate from core aider functionality
- Use aider's existing IO and command infrastructure
- Maintain aider's existing test patterns and structure
- All changes must be backward compatible with existing aider workflows

## Governance

### Decision Making
- Technical decisions must align with aider's existing architecture
- New functionality should extend, not replace, existing aider capabilities
- Changes should be minimal and focused on the specific SpecKit integration need

### Quality Gates
- All new code must have corresponding tests
- Integration must work with aider's existing command system
- Error handling must follow aider's patterns
- Documentation must be clear and concise

### Compatibility Requirements
- Must work with aider's existing repository discovery
- Must integrate cleanly with aider's command system
- Must respect aider's existing file handling patterns
- Must not interfere with aider's core editing functionality
