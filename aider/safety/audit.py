# Logging Safety audit events/decisions for Aider

"""
Audit Logging for Safety Decisions
Tracks all safety checks for compliance and debugging
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager


class SafetyAuditLogger:
    """
    Log all safety decisions to SQLite database
    
    Why SQLite?
    - No external dependencies
    - Queryable (unlike flat files)
    - ACID compliant
    - Perfect for local dev tools
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize audit logger
        
        Args:
            db_path: Path to SQLite database (default: ~/.aider/safety_audit.db)
        """
        if db_path is None:
            # Use default location in user's home
            aider_dir = Path.home() / '.aider'
            aider_dir.mkdir(exist_ok=True)
            db_path = str(aider_dir / 'safety_audit.db')
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS safety_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON safety_checks(timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_risk_score 
                ON safety_checks(risk_score)
            ''')
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return dict-like rows
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def log_safety_check(
        self,
        safety_result,
        filename: str = "",
        code_snippet: str = "",
        user_approved: Optional[bool] = None
    ) -> int:
        """
        Log a safety check result
        
        Args:
            safety_result: SafetyResult object
            filename: File being checked
            code_snippet: The code that was checked
            user_approved: Whether user approved (None if no confirmation needed)
        
        Returns:
            int: ID of the logged entry
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO safety_checks (
                    timestamp, filename, code_snippet, is_safe, risk_score,
                    requires_confirmation, user_approved, violations_json, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                filename,
                code_snippet[:1000],  # Truncate long code
                safety_result.is_safe,
                safety_result.risk_score,
                safety_result.requires_confirmation,
                user_approved,
                json.dumps([v.to_dict() for v in safety_result.violations]),
                safety_result.message
            ))
            
            return cursor.lastrowid
    
    def get_recent_checks(self, limit: int = 10) -> list:
        """Get recent safety checks"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM safety_checks
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_high_risk_checks(self, risk_threshold: float = 0.6) -> list:
        """Get all high-risk checks"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM safety_checks
                WHERE risk_score >= ?
                ORDER BY risk_score DESC, timestamp DESC
            ''', (risk_threshold,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """Get audit statistics"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN requires_confirmation THEN 1 ELSE 0 END) as confirmations_required,
                    SUM(CASE WHEN user_approved = 1 THEN 1 ELSE 0 END) as user_approved,
                    SUM(CASE WHEN user_approved = 0 THEN 1 ELSE 0 END) as user_rejected,
                    AVG(risk_score) as avg_risk_score,
                    MAX(risk_score) as max_risk_score
                FROM safety_checks
            ''')
            
            return dict(cursor.fetchone())


# Global instance
_audit_logger = None

def get_audit_logger() -> SafetyAuditLogger:
    """Get or create global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = SafetyAuditLogger()
    return _audit_logger