# Core Safety checks for Aider

"""
Safety Guardrails for Aider
Implements Constitutional AI-inspired safety checks
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .config import SafetyConfig, RiskLevel, SafetyRule


@dataclass
class SafetyViolation:
    """A detected safety violation"""
    rule: SafetyRule
    matched_text: str
    line_number: int
    context: str  # Surrounding code for context
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            'category': self.rule.category,
            'risk_level': self.rule.risk_level.value,
            'description': self.rule.description,
            'matched_text': self.matched_text,
            'line_number': self.line_number,
            'context': self.context,
            'example': self.rule.example
        }


@dataclass
class SafetyResult:
    """Result of safety check"""
    is_safe: bool
    violations: List[SafetyViolation] = field(default_factory=list)
    risk_score: float = 0.0
    requires_confirmation: bool = False
    message: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'is_safe': self.is_safe,
            'violations': [v.to_dict() for v in self.violations],
            'risk_score': self.risk_score,
            'requires_confirmation': self.requires_confirmation,
            'message': self.message,
            'timestamp': datetime.now().isoformat()
        }


class SafetyGuardrails:
    """
    Constitutional AI-inspired safety system for code generation
    
    Key Principles:
    1. Defense in Depth: Multiple layers of checks
    2. Transparency: Clear explanations of why something is flagged
    3. Human Oversight: Require confirmation for risky operations
    4. Auditability: Log all safety decisions
    """
    
    def __init__(self, config: SafetyConfig = None):
        self.config = config or SafetyConfig()
        self.stats = {
            'total_checks': 0,
            'violations_found': 0,
            'confirmations_required': 0,
            'blocked': 0
        }
    
    def check_code(self, code: str, filename: str = "") -> SafetyResult:
        """
        Main safety check method
        
        Args:
            code: The generated code to check
            filename: Name of file being modified (for context)
        
        Returns:
            SafetyResult with violations and recommendations
        """
        self.stats['total_checks'] += 1
        
        violations = []
        lines = code.split('\n')
        
        # Check each safety rule
        for rule in self.config.SAFETY_RULES:
            pattern = re.compile(rule.pattern, re.IGNORECASE | re.MULTILINE)
            
            # Search through code
            for line_num, line in enumerate(lines, start=1):
                matches = pattern.finditer(line)
                
                for match in matches:
                    # Get context (3 lines before and after)
                    context_start = max(0, line_num - 3)
                    context_end = min(len(lines), line_num + 3)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    violation = SafetyViolation(
                        rule=rule,
                        matched_text=match.group(),
                        line_number=line_num,
                        context=context
                    )
                    violations.append(violation)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(violations)
        
        # Determine if confirmation needed
        requires_confirmation = any(
            v.rule.risk_level in self.config.REQUIRE_CONFIRMATION
            for v in violations
        )
        
        # Build result
        if not violations:
            return SafetyResult(
                is_safe=True,
                message="✅ No safety concerns detected"
            )
        
        # We have violations
        self.stats['violations_found'] += len(violations)
        
        if requires_confirmation:
            self.stats['confirmations_required'] += 1
        
        message = self._build_safety_message(violations, requires_confirmation)
        
        return SafetyResult(
            is_safe=not requires_confirmation,  # Safe if no confirmation needed
            violations=violations,
            risk_score=risk_score,
            requires_confirmation=requires_confirmation,
            message=message
        )
    
    def _calculate_risk_score(self, violations: List[SafetyViolation]) -> float:
        """
        Calculate overall risk score (0.0 to 1.0)
        
        Formula: Weighted sum based on risk levels
        """
        if not violations:
            return 0.0
        
        risk_weights = {
            RiskLevel.LOW: 0.1,
            RiskLevel.MEDIUM: 0.3,
            RiskLevel.HIGH: 0.6,
            RiskLevel.CRITICAL: 1.0
        }
        
        total_score = sum(
            risk_weights.get(v.rule.risk_level, 0)
            for v in violations
        )
        
        # Normalize (cap at 1.0)
        return min(total_score / len(violations), 1.0)
    
    def _build_safety_message(
        self, 
        violations: List[SafetyViolation],
        requires_confirmation: bool
    ) -> str:
        """Build human-readable safety message"""
        
        # Group by category
        by_category = {}
        for v in violations:
            category = v.rule.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(v)
        
        # Build message
        lines = []
        lines.append("⚠️  SAFETY ALERT: Potentially dangerous operations detected\n")
        
        for category, cat_violations in by_category.items():
            lines.append(f"\n📋 {category.upper()} ({len(cat_violations)} issues):")
            
            for i, v in enumerate(cat_violations[:3], 1):  # Show max 3 per category
                lines.append(f"  {i}. Line {v.line_number}: {v.rule.description}")
                lines.append(f"     Found: `{v.matched_text}`")
                lines.append(f"     Risk: {v.rule.risk_level.value.upper()}")
        
        if requires_confirmation:
            lines.append("\n❓ HUMAN CONFIRMATION REQUIRED")
            lines.append("   These operations can be destructive.")
            lines.append("   Please review carefully before proceeding.")
        else:
            lines.append("\n⚡ These are warnings only.")
            lines.append("   Code will proceed but has been flagged for review.")
        
        return '\n'.join(lines)
    
    def get_stats(self) -> dict:
        """Get safety statistics"""
        return self.stats.copy()


# Convenience function
def check_code_safety(code: str, filename: str = "") -> SafetyResult:
    """
    Quick safety check function
    
    Usage:
        result = check_code_safety(generated_code)
        if result.requires_confirmation:
            # Ask user for confirmation
            pass
    """
    guardrails = SafetyGuardrails()
    return guardrails.check_code(code, filename)