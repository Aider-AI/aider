# Safety rules consifigurations for Aider

"""
Safety Configuration for Aider
Defines dangerous patterns and risk levels
"""

from enum import Enum
from typing import Dict, List
from dataclasses import dataclass


class RiskLevel(Enum):
    """Risk levels for operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyRule:
    """A single safety rule"""
    pattern: str
    category: str
    risk_level: RiskLevel
    description: str
    example: str


class SafetyConfig:
    """
    Configuration for safety checks
    
    Inspired by Anthropic's Constitutional AI:
    - Define clear principles
    - Categorize by risk
    - Require human oversight for high-risk operations
    """
    
    # Dangerous patterns organized by category
    SAFETY_RULES: List[SafetyRule] = [
        # CRITICAL: Code Execution
        SafetyRule(
            pattern=r"os\.system\s*\(",
            category="code_execution",
            risk_level=RiskLevel.CRITICAL,
            description="Direct shell command execution",
            example="os.system('rm -rf /')"
        ),
        SafetyRule(
            pattern=r"subprocess\.(call|run|Popen)\s*\(",
            category="code_execution",
            risk_level=RiskLevel.CRITICAL,
            description="Subprocess execution",
            example="subprocess.call(['rm', '-rf', '/'])"
        ),
        SafetyRule(
            pattern=r"\beval\s*\(",
            category="code_execution",
            risk_level=RiskLevel.CRITICAL,
            description="Dynamic code evaluation",
            example="eval(user_input)"
        ),
        SafetyRule(
            pattern=r"\bexec\s*\(",
            category="code_execution",
            risk_level=RiskLevel.CRITICAL,
            description="Dynamic code execution",
            example="exec(malicious_code)"
        ),
        
        # HIGH: Destructive File Operations
        SafetyRule(
            pattern=r"os\.remove\s*\(",
            category="file_operations",
            risk_level=RiskLevel.HIGH,
            description="File deletion",
            example="os.remove('/important/file')"
        ),
        SafetyRule(
            pattern=r"shutil\.rmtree\s*\(",
            category="file_operations",
            risk_level=RiskLevel.HIGH,
            description="Recursive directory deletion",
            example="shutil.rmtree('/entire/directory')"
        ),
        SafetyRule(
            pattern=r"os\.rmdir\s*\(",
            category="file_operations",
            risk_level=RiskLevel.HIGH,
            description="Directory removal",
            example="os.rmdir('/directory')"
        ),
        SafetyRule(
            pattern=r"\brm\s+-rf\b",
            category="shell_commands",
            risk_level=RiskLevel.CRITICAL,
            description="Dangerous shell command in string",
            example="'rm -rf /'"
        ),
        
        # HIGH: Network Operations
        SafetyRule(
            pattern=r"requests\.(post|put|delete)\s*\(",
            category="network",
            risk_level=RiskLevel.HIGH,
            description="HTTP write operations",
            example="requests.post('http://api.com', data=sensitive)"
        ),
        SafetyRule(
            pattern=r"urllib\.request\.(urlopen|Request)\s*\(",
            category="network",
            risk_level=RiskLevel.MEDIUM,
            description="Network requests",
            example="urllib.request.urlopen('http://malicious.com')"
        ),
        SafetyRule(
            pattern=r"socket\.(connect|bind)\s*\(",
            category="network",
            risk_level=RiskLevel.HIGH,
            description="Direct socket operations",
            example="socket.connect(('0.0.0.0', 80))"
        ),
        
        # MEDIUM: Credential Handling
        SafetyRule(
            pattern=r"(password|passwd|pwd)\s*=\s*['\"]",
            category="credentials",
            risk_level=RiskLevel.MEDIUM,
            description="Hardcoded password",
            example="password = 'secret123'"
        ),
        SafetyRule(
            pattern=r"(api_key|apikey|api-key)\s*=\s*['\"]",
            category="credentials",
            risk_level=RiskLevel.MEDIUM,
            description="Hardcoded API key",
            example="api_key = 'sk-abc123'"
        ),
        SafetyRule(
            pattern=r"(secret|token|auth)\s*=\s*['\"]",
            category="credentials",
            risk_level=RiskLevel.MEDIUM,
            description="Hardcoded secret",
            example="secret = 'my_secret_token'"
        ),
        
        # MEDIUM: Database Operations
        SafetyRule(
            pattern=r"DROP\s+(TABLE|DATABASE)\b",
            category="database",
            risk_level=RiskLevel.HIGH,
            description="Database deletion",
            example="DROP TABLE users"
        ),
        SafetyRule(
            pattern=r"TRUNCATE\s+TABLE\b",
            category="database",
            risk_level=RiskLevel.HIGH,
            description="Table truncation",
            example="TRUNCATE TABLE logs"
        ),
    ]
    
    @classmethod
    def get_rules_by_risk(cls, risk_level: RiskLevel) -> List[SafetyRule]:
        """Get all rules of a specific risk level"""
        return [rule for rule in cls.SAFETY_RULES if rule.risk_level == risk_level]
    
    @classmethod
    def get_rules_by_category(cls, category: str) -> List[SafetyRule]:
        """Get all rules in a category"""
        return [rule for rule in cls.SAFETY_RULES if rule.category == category]
    
    # Human confirmation required for these risk levels
    REQUIRE_CONFIRMATION = [RiskLevel.HIGH, RiskLevel.CRITICAL]
    
    # Automatically block these (no confirmation)
    AUTO_BLOCK = []  # Empty for now but we will warn for everything