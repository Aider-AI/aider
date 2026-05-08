# SpecKit MTARP Bootstrap Integration

## Overview

Integrate a minimal SpecKit-compatible workflow into aider-relay that can discover SpecKit-style artifacts, report their status, and later generate MTARP task snapshots.

## User Stories

### As a developer using aider-relay
- I want to discover SpecKit artifacts in my repository so I can see what specifications exist
- I want to check the status of SpecKit artifacts so I can understand project readiness
- I want clear error messages when multiple specs exist but no feature is specified
- I want the tool to work offline without requiring LLM calls for basic discovery

### As a project maintainer
- I want SpecKit artifact discovery to be separate from MTARP execution state
- I want deterministic MTARP snapshots in YAML or JSON format
- I want the integration to be compatible with upstream aider changes
- I want the implementation to follow aider's existing patterns and conventions

## Functional Requirements

### Artifact Discovery
- **FR-001**: Discover `.specify/memory/constitution.md` files
- **FR-002**: Discover `specs/<feature>/spec.md` files  
- **FR-003**: Discover `specs/<feature>/plan.md` files
- **FR-004**: Discover `specs/<feature>/tasks.md` files
- **FR-005**: If exactly one `specs/*` directory exists, select it by default
- **FR-006**: If multiple `specs/*` directories exist and no feature is specified, return clear error

### Status Reporting
- **FR-007**: Report found/missing artifacts in human-readable format
- **FR-008**: Report whether feature is ready for MTARP snapshot generation
- **FR-009**: Provide summary statistics (total files, directories, etc.)
- **FR-010**: Handle empty repositories gracefully

### Command Integration
- **FR-011**: Implement `/speckit status` command following aider's command patterns
- **FR-012**: Integrate with aider's existing IO and error handling
- **FR-013**: Use aider's repository root discovery mechanism
- **FR-014**: Follow aider's command help and documentation patterns

## Non-Functional Requirements

### Compatibility
- **NFR-001**: Must work offline without LLM calls
- **NFR-002**: Must not modify SpecKit artifacts (read-only in first implementation)
- **NFR-003**: Must be compatible with upstream aider changes
- **NFR-004**: Must follow aider's existing code patterns and conventions

### Performance
- **NFR-005**: Artifact discovery must complete in under 1 second for typical repositories
- **NFR-006**: Must handle repositories with hundreds of spec directories efficiently

### Maintainability
- **NFR-007**: Implementation must be in small, testable modules
- **NFR-008**: Must have comprehensive test coverage
- **NFR-009**: Must use aider's existing infrastructure where possible

## Acceptance Criteria

### Discovery Functionality
- [ ] Can discover constitution.md in .specify/memory/
- [ ] Can discover spec.md files in specs/<feature>/ directories
- [ ] Can discover plan.md files in specs/<feature>/ directories  
- [ ] Can discover tasks.md files in specs/<feature>/ directories
- [ ] Handles missing files gracefully
- [ ] Provides clear error for multiple specs without feature specification

### Status Reporting
- [ ] Generates human-readable status report
- [ ] Shows found vs missing artifacts
- [ ] Provides summary statistics
- [ ] Indicates MTARP readiness
- [ ] Handles empty repositories without errors

### Command Integration
- [ ] `/speckit status` command works in aider
- [ ] Integrates with aider's help system
- [ ] Uses aider's error handling patterns
- [ ] Respects aider's repository root detection
- [ ] Works with aider's existing IO system

### Quality Assurance
- [ ] All functionality has unit tests
- [ ] Integration tests cover command execution
- [ ] Code follows aider's style and patterns
- [ ] Documentation is complete and accurate
- [ ] No regressions in existing aider functionality

## Out of Scope (Future Phases)

- Creating or modifying SpecKit artifacts
- `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement` commands
- MTARP snapshot generation and execution
- LLM integration for artifact generation
- Multi-feature orchestration
- Artifact validation beyond existence checks

## References

- GitHub Spec Kit: https://github.com/github/spec-kit
- Aider command system: `aider/commands.py`
- Aider IO patterns: `aider/io.py`
- Existing aider tests: `tests/` directory
