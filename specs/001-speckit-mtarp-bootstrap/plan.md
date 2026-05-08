# Implementation Plan: SpecKit MTARP Bootstrap Integration

## Architecture Overview

### Component Structure
```
aider/
├── speckit.py              # Core SpecKit discovery logic
├── commands.py             # Extended with /speckit command
└── tests/
    └── test_speckit.py     # Comprehensive test suite
```

### Design Principles
- **Separation of Concerns**: SpecKit logic isolated in dedicated module
- **Aider Integration**: Leverage existing command, IO, and repository infrastructure  
- **Testability**: Small, focused functions with clear interfaces
- **Extensibility**: Foundation for future MTARP snapshot generation

## Technical Implementation

### Core Discovery Module (`aider/speckit.py`)

#### SpecKitDiscovery Class
```python
class SpecKitDiscovery:
    def __init__(self, root_path: str)
    def discover_artifacts(self) -> Dict[str, Any]
    def format_status_report(self, artifacts: Dict[str, Any]) -> str
```

**Key Responsibilities:**
- Scan repository for SpecKit artifacts using pathlib.Path.rglob()
- Categorize findings (constitution, specs, plans, tasks)
- Generate human-readable status reports
- Determine MTARP readiness based on artifact completeness

**Artifact Discovery Logic:**
- Constitution: `.specify/memory/constitution.md`
- Spec files: `specs/*/spec.md` pattern matching
- Plan files: `specs/*/plan.md` pattern matching  
- Task files: `specs/*/tasks.md` pattern matching
- Test files: `*test*.py`, `test_*.py` patterns for compatibility

### Command Integration (`aider/commands.py`)

#### Command Structure
```python
def cmd_speckit(self, args):
    """SpecKit integration commands (status)"""
    
def _cmd_speckit_status(self):
    """Show status of SpecKit artifacts in the repository."""
```

**Integration Points:**
- Extend existing Commands class following established patterns
- Use `self.coder.root` for repository root access
- Leverage `self.io.tool_output()` and `self.io.tool_error()` for user feedback
- Follow aider's argument parsing and error handling conventions

### Error Handling Strategy

#### Repository State Validation
- **No Repository Root**: Clear error message with guidance
- **Empty Repository**: Graceful handling with "no artifacts found" message
- **Multiple Specs**: Specific error explaining feature selection requirement
- **Discovery Errors**: Catch and report filesystem access issues

#### User Experience
- Consistent error message formatting using aider's IO patterns
- Helpful guidance for next steps
- Clear distinction between expected states and actual errors

## Data Structures

### Artifact Discovery Response
```python
{
    "constitution": str,               # Path to constitution.md if found
    "spec_files": List[str],           # Relative paths to spec.md files
    "spec_directories": List[str],     # Spec directory names
    "test_files": List[str],          # Test file paths
    "summary": {
        "total_spec_files": int,
        "total_spec_directories": int, 
        "total_test_files": int,
        "has_speckit_artifacts": bool,
        "mtarp_ready": bool
    }
}
```

### Status Report Format
```
SpecKit Status Report
====================

Constitution: ✓ Found (.specify/memory/constitution.md)

Spec Directories (2):
  - specs/001-speckit-mtarp-bootstrap/ ✓ Complete (spec.md, plan.md, tasks.md)
  - specs/002-feature/ ⚠ Incomplete (missing plan.md, tasks.md)

Test Files (5):
  - tests/test_speckit.py
  - tests/test_integration.py

Summary:
  Total spec files: 2
  Total spec directories: 2  
  Total test files: 5
  MTARP Ready: ✓ Yes (constitution + 1 complete spec)
```

## Testing Strategy

### Unit Tests (`tests/test_speckit.py`)

#### SpecKitDiscovery Tests
- **Empty repository discovery**: Verify graceful handling of no artifacts
- **Constitution discovery**: Test `.specify/memory/constitution.md` detection
- **Single spec discovery**: Test discovery of complete spec directory
- **Multiple spec discovery**: Verify discovery of multiple spec directories
- **Partial artifact discovery**: Test handling of incomplete spec directories
- **Test file discovery**: Validate test file pattern matching
- **MTARP readiness**: Test readiness calculation logic

#### Status Report Tests  
- **Empty report formatting**: Verify "no artifacts" message
- **Complete report formatting**: Test full status report generation
- **Summary calculation**: Validate summary statistics accuracy
- **MTARP readiness display**: Test readiness indicator formatting

### Integration Tests

#### Command Integration Tests
- **Command registration**: Verify `/speckit` command availability
- **Argument parsing**: Test subcommand routing (`status`)
- **Error handling**: Validate error message formatting and routing
- **Repository integration**: Test with aider's repository root detection

#### End-to-End Tests
- **Real repository testing**: Test against actual spec directory structures
- **Cross-platform compatibility**: Verify Windows/Linux/macOS path handling
- **Performance validation**: Ensure sub-second response times

## Implementation Phases

### Phase 1: Enhanced Discovery (Current)
- [x] Implement enhanced SpecKitDiscovery class
- [x] Add constitution.md discovery
- [x] Add complete spec directory detection (spec.md + plan.md + tasks.md)
- [x] Add MTARP readiness calculation
- [x] Update command integration
- [x] Implement comprehensive test suite

### Phase 2: MTARP Integration (Future)
- [ ] MTARP snapshot generation from discovered artifacts
- [ ] Task execution state tracking
- [ ] Integration with aider's editing workflow
- [ ] Bidirectional sync between specs and implementation

### Phase 3: Full SpecKit Commands (Future)
- [ ] `/speckit.specify` for spec creation
- [ ] `/speckit.plan` for plan generation  
- [ ] `/speckit.tasks` for task breakdown
- [ ] `/speckit.implement` for execution

## Dependencies

### Required Libraries
- **pathlib**: File system traversal (Python standard library)
- **typing**: Type hints for better code documentation
- **json/yaml**: Future MTARP snapshot serialization

### Aider Integration Points
- **aider.commands.Commands**: Base class for command implementation
- **aider.io.InputOutput**: User interaction and error reporting
- **Repository root detection**: Via `self.coder.root`
- **Test infrastructure**: Existing pytest setup and patterns

## Risk Mitigation

### Compatibility Risks
- **Upstream aider changes**: Minimize dependencies on internal aider APIs
- **Path handling**: Use pathlib for cross-platform compatibility
- **Command conflicts**: Use unique `/speckit` namespace

### Performance Risks  
- **Large repositories**: Implement efficient directory traversal
- **Deep directory structures**: Limit recursion depth if needed
- **File system access**: Handle permission errors gracefully

### Maintainability Risks
- **Code complexity**: Keep functions small and focused
- **Test coverage**: Maintain comprehensive test suite
- **Documentation**: Clear docstrings and inline comments

## Success Metrics

### Functional Metrics
- All acceptance criteria met
- 100% test coverage for new code
- Sub-second response time for typical repositories
- Zero regressions in existing aider functionality

### Quality Metrics
- Code passes all existing aider linting and style checks
- Integration tests pass on all supported platforms
- Documentation is complete and accurate
- Error messages are clear and actionable

### Compatibility Metrics
- Works with aider's existing command system
- Respects aider's repository detection logic
- Follows aider's error handling patterns
- Maintains backward compatibility
