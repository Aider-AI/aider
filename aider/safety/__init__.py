"""
Safety Module for Aider
Provides Constitutional AI-inspired safety guardrails
"""

from .guardrails import (
    SafetyGuardrails,
    SafetyResult,
    SafetyViolation,
    check_code_safety
)
from .config import SafetyConfig, RiskLevel, SafetyRule
from .audit import SafetyAuditLogger, get_audit_logger

__all__ = [
    'SafetyGuardrails',
    'SafetyResult',
    'SafetyViolation',
    'SafetyConfig',
    'RiskLevel',
    'SafetyRule',
    'SafetyAuditLogger',
    'get_audit_logger',
    'check_code_safety',
]

__version__ = '1.0.0'