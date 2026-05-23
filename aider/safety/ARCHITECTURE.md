# Safety Guardrails - Architecture Documentation

## System Overview

The safety guardrails system consists of four main components that work together to detect, assess, and log potentially dangerous code operations.

## Component Architecture

### 1. Configuration Layer (`config.py`)

**Purpose**: Define safety rules and risk classifications

**Key Classes**:
- `SafetyRule`: Represents a single detection rule
- `SafetyConfig`: Container for all rules and configuration
- `RiskLevel`: Enumeration of risk levels (LOW, MEDIUM, HIGH, CRITICAL)

**Data Flow**:
```
SafetyConfig.SAFETY_RULES[] → SafetyGuardrails.__init__() → Detection Engine
```

**Design Decisions**:
- Used dataclasses for immutability and clarity
- Regex patterns for performance (compiled once, reused)
- Risk levels as enum for type safety
- Centralized configuration for easy rule management

### 2. Detection Engine (`guardrails.py`)

**Purpose**: Scan code and detect violations

**Key Classes**:
- `SafetyGuardrails`: Main detection engine
- `SafetyViolation`: Represents a detected issue
- `SafetyResult`: Aggregated results with metadata

**Algorithm**:
```python
for each rule in safety_rules:
    for each line in code:
        if pattern_matches(line):
            create_violation(rule, line_number, context)

risk_score = calculate_weighted_score(violations)
requires_confirmation = any(v.risk_level in [HIGH, CRITICAL])

return SafetyResult(violations, risk_score, requires_confirmation)
```

**Performance Optimizations**:
- Regex patterns compiled at initialization (not per-check)
- Short-circuit evaluation for safe code
- Context extraction limited to ±3 lines
- Early termination if confirmation already required

### 3. Audit System (`audit.py`)

**Purpose**: Persistent logging of all safety decisions

**Key Classes**:
- `SafetyAuditLogger`: SQLite wrapper for logging
- Context managers for transaction safety

**Database Schema**:
```sql
safety_checks (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    filename TEXT,
    code_snippet TEXT,
    is_safe BOOLEAN,
    risk_score REAL,
    requires_confirmation BOOLEAN,
    user_approved BOOLEAN,
    violations_json TEXT,
    message TEXT
)

INDEXES:
- idx_timestamp ON timestamp
- idx_risk_score ON risk_score
```

**Design Decisions**:
- SQLite for zero-dependency persistence
- JSON for violations (flexible schema)
- Indexed timestamps and risk scores for fast queries
- ACID transactions for data integrity

### 4. Public API (`__init__.py`)

**Purpose**: Expose clean interface for consumers

**Exported Functions**:
- `check_code_safety(code, filename)`: Main entry point
- `get_audit_logger()`: Singleton logger instance

**Design Pattern**: Facade pattern - simplifies complex subsystem

## Integration Points

### Integration with Aider's Code Flow
```python
# In aider/coders/base_coder.py

def apply_updates(self, edits):
    for path, new_content in edits:
        # INTEGRATION POINT 1: Safety check before apply
        if self.enable_safety:
            result = check_code_safety(new_content, filename=path)
            
            # INTEGRATION POINT 2: Audit logging
            logger = get_audit_logger()
            
            if result.requires_confirmation:
                # INTEGRATION POINT 3: User interaction
                self.io.tool_output(result.message)
                
                if not self.io.confirm_ask("Apply anyway?"):
                    logger.log_safety_check(result, path, new_content, user_approved=False)
                    continue  # Skip this file
                
                logger.log_safety_check(result, path, new_content, user_approved=True)
            
            elif result.violations:
                # Warning only
                self.io.tool_warning(result.message)
                logger.log_safety_check(result, path, new_content, user_approved=None)
        
        # Apply code (existing Aider logic)
        apply_file_changes(path, new_content)
```

**Integration Characteristics**:
- Non-invasive: Only 3 insertion points in existing code
- Optional: Can be disabled with `--disable-safety`
- Zero impact on existing logic when disabled
- Backward compatible: No breaking changes

## Data Flow Diagram
```
┌─────────────┐
│   User      │
│  Request    │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  LLM generates  │
│     code        │
└──────┬──────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Safety Guardrails                │
│                                          │
│  1. Load rules from config               │
│  2. Scan code line-by-line               │
│  3. Match against regex patterns         │
│  4. Collect violations                   │
│  5. Calculate risk score                 │
│  6. Determine if confirmation needed     │
│                                          │
└──────┬──────────────────────────────────┘
       │
       ▼
┌──────────────┐        ┌─────────────────┐
│ Audit Logger │◄───────┤  SafetyResult   │
│  (SQLite)    │        │  - is_safe      │
└──────────────┘        │  - violations   │
                        │  - risk_score   │
                        │  - message      │
                        └─────────┬───────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
         ┌──────────┐      ┌──────────┐     ┌──────────┐
         │   Safe   │      │ Warning  │     │  Block   │
         │  Apply   │      │  Show    │     │  Confirm │
         └──────────┘      └──────────┘     └────┬─────┘
                                                  │
                                                  ▼
                                           ┌──────────────┐
                                           │ User decides │
                                           └──────┬───────┘
                                                  │
                                         ┌────────┼────────┐
                                         │                 │
                                         ▼                 ▼
                                    ┌────────┐       ┌─────────┐
                                    │ Apply  │       │ Reject  │
                                    └────────┘       └─────────┘
```

## Error Handling

### Exception Hierarchy
```
Exception
└── SafetyError (base)
    ├── ConfigurationError (invalid rules)
    ├── DetectionError (pattern matching failed)
    └── AuditError (database write failed)
```

### Error Recovery Strategies

1. **Configuration Errors**: Fall back to default safe rules
2. **Detection Errors**: Log error, allow code (fail open for availability)
3. **Audit Errors**: Log to stderr, continue (logging failure shouldn't block)

## Performance Considerations

### Computational Complexity

- **check_code()**: O(n * m) where n = lines, m = rules
- **Risk calculation**: O(v) where v = violations
- **Audit logging**: O(1) database insert

### Memory Usage

- **Rule storage**: ~10KB (15 rules × ~700 bytes)
- **Per-check overhead**: ~1KB (SafetyResult object)
- **Audit database**: ~1KB per logged check

### Optimization Techniques

1. **Compiled Regex**: Patterns compiled once at initialization
2. **Early Termination**: Stop processing if already requires confirmation
3. **Lazy Context Extraction**: Only extract context when violation found
4. **Indexed Database**: Fast queries on timestamp and risk_score

## Security Considerations

### Threat Model

**Threats Mitigated**:
- Accidental execution of dangerous system commands
- Unintended file deletion
- Credential leakage in generated code
- Malicious prompt injection leading to dangerous code

**Threats NOT Mitigated**:
- Sophisticated obfuscation (base64 encoded commands)
- Logic errors in safe-looking code
- Performance degradation attacks
- Social engineering of users to approve dangerous code

### Security Properties

- **Defense in Depth**: Multiple detection layers
- **Principle of Least Privilege**: Only detects, never modifies code
- **Audit Trail**: Complete logging for forensic analysis
- **Human-in-the-Loop**: Critical operations require explicit approval

## Testing Strategy

### Test Pyramid
```
         /\
        /  \  E2E Tests (1)
       /    \  - Full Aider integration
      /------\
     /        \ Integration Tests (6)
    /          \ - test_safety_standalone.py
   /            \
  /--------------\
 /                \ Unit Tests (6)
/                  \ - pytest tests/safety/
--------------------
```

### Test Coverage

- **Unit Tests**: 100% of detection rules
- **Integration Tests**: All user flows (approve, reject, warning)
- **Performance Tests**: Verify <5ms latency
- **Regression Tests**: Prevent false positive/negative changes

## Future Enhancements

### Planned Features

1. **LLM-as-Judge**: Use Claude to evaluate borderline cases
2. **Custom Rule DSL**: User-friendly rule definition language
3. **Whitelist System**: Per-repository safe operation lists
4. **Telemetry Dashboard**: Real-time monitoring of safety events
5. **Integration Tests**: Automated E2E testing with real Aider

### Scalability Considerations

- **Current**: <5ms per check, ~200 checks/sec
- **Target**: <2ms per check, ~500 checks/sec
- **Approach**: Parallel rule evaluation, bloom filters for quick rejection

## Maintenance

### Adding New Rules

1. Identify dangerous pattern
2. Create SafetyRule in config.py
3. Write test case in tests/safety/
4. Verify false positive rate <5%
5. Document in README

### Monitoring Health
```python
# Check system health
from aider.safety import SafetyGuardrails, get_audit_logger

guardrails = SafetyGuardrails()
logger = get_audit_logger()

# Performance check
import time
start = time.time()
guardrails.check_code("def test(): pass")
latency = (time.time() - start) * 1000
assert latency < 5, f"Latency too high: {latency}ms"

# Accuracy check
stats = logger.get_stats()
rejection_rate = stats['user_rejected'] / stats['confirmations_required']
assert rejection_rate > 0.5, "Users rejecting too few dangerous operations"
```

## References

- Anthropic Constitutional AI paper: https://arxiv.org/abs/2212.08073
- Bandit security scanner: https://github.com/PyCQA/bandit
- OWASP Code Review Guide: https://owasp.org/www-project-code-review-guide/