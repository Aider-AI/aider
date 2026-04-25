"""
Metrics Store for Observability
Local SQLite storage for LLM usage metrics
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager
from dataclasses import dataclass, asdict


@dataclass
class MetricEntry:
    """Single metric entry"""
    id: Optional[int] = None
    timestamp: str = ""
    run_id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    prompt_type: str = ""  # e.g., "code_generation", "chat", "edit"
    metadata: str = "{}"  # JSON string
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if k != 'id'}


class MetricsStore:
    """
    Local SQLite store for observability metrics
    
    Stores:
    - Token usage per request
    - Cost per request
    - Latency per request
    - Success/failure rates
    - Model usage patterns
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize metrics store
        
        Args:
            db_path: Path to SQLite database (default: ~/.aider/observability.db)
        """
        if db_path is None:
            aider_dir = Path.home() / '.aider'
            aider_dir.mkdir(exist_ok=True)
            db_path = str(aider_dir / 'observability.db')
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    latency_ms REAL NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    prompt_type TEXT,
                    metadata TEXT
                )
            ''')
            
            # Create indexes for fast queries
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON metrics(timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_model 
                ON metrics(model)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_success 
                ON metrics(success)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_run_id 
                ON metrics(run_id)
            ''')
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def log_metric(
        self,
        run_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        success: bool = True,
        error_message: Optional[str] = None,
        prompt_type: str = "",
        metadata: Optional[dict] = None
    ) -> int:
        """
        Log a metric entry
        
        Args:
            run_id: Unique identifier for this run (LangSmith run ID)
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
            latency_ms: Latency in milliseconds
            success: Whether the request succeeded
            error_message: Error message if failed
            prompt_type: Type of prompt (code_generation, chat, etc.)
            metadata: Additional metadata as dict
        
        Returns:
            int: ID of logged entry
        """
        total_tokens = input_tokens + output_tokens
        metadata_json = json.dumps(metadata or {})
        
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO metrics (
                    timestamp, run_id, model, input_tokens, output_tokens,
                    total_tokens, cost_usd, latency_ms, success,
                    error_message, prompt_type, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                run_id,
                model,
                input_tokens,
                output_tokens,
                total_tokens,
                cost_usd,
                latency_ms,
                success,
                error_message,
                prompt_type,
                metadata_json
            ))
            
            return cursor.lastrowid
    
    def get_metrics(
        self,
        limit: int = 100,
        model: Optional[str] = None,
        success_only: bool = False
    ) -> List[MetricEntry]:
        """
        Get recent metrics
        
        Args:
            limit: Maximum number of entries to return
            model: Filter by model (None = all models)
            success_only: Only return successful requests
        
        Returns:
            List of MetricEntry objects
        """
        query = "SELECT * FROM metrics WHERE 1=1"
        params = []
        
        if model:
            query += " AND model = ?"
            params.append(model)
        
        if success_only:
            query += " AND success = 1"
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                entry = MetricEntry(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    run_id=row['run_id'],
                    model=row['model'],
                    input_tokens=row['input_tokens'],
                    output_tokens=row['output_tokens'],
                    total_tokens=row['total_tokens'],
                    cost_usd=row['cost_usd'],
                    latency_ms=row['latency_ms'],
                    success=bool(row['success']),
                    error_message=row['error_message'],
                    prompt_type=row['prompt_type'],
                    metadata=row['metadata']
                )
                entries.append(entry)
            
            return entries
    
    def get_statistics(
        self,
        hours: int = 24,
        model: Optional[str] = None
    ) -> Dict:
        """
        Get aggregated statistics
        
        Args:
            hours: Time window in hours
            model: Filter by model (None = all models)
        
        Returns:
            Dictionary with aggregated stats
        """
        query = """
            SELECT 
                COUNT(*) as total_requests,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_requests,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost_usd,
                AVG(latency_ms) as avg_latency_ms,
                MIN(latency_ms) as min_latency_ms,
                MAX(latency_ms) as max_latency_ms,
                AVG(cost_usd) as avg_cost_usd
            FROM metrics
            WHERE datetime(timestamp) >= datetime('now', '-' || ? || ' hours')
        """
        
        params = [hours]
        
        if model:
            query += " AND model = ?"
            params.append(model)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            if not row or row['total_requests'] == 0:
                return {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'success_rate': 0.0,
                    'total_tokens': 0,
                    'total_cost_usd': 0.0,
                    'avg_latency_ms': 0.0,
                    'avg_cost_usd': 0.0
                }
            
            return {
                'total_requests': row['total_requests'],
                'successful_requests': row['successful_requests'],
                'failed_requests': row['failed_requests'],
                'success_rate': (row['successful_requests'] / row['total_requests']) * 100,
                'total_input_tokens': row['total_input_tokens'],
                'total_output_tokens': row['total_output_tokens'],
                'total_tokens': row['total_tokens'],
                'total_cost_usd': round(row['total_cost_usd'], 4),
                'avg_latency_ms': round(row['avg_latency_ms'], 2),
                'min_latency_ms': round(row['min_latency_ms'], 2),
                'max_latency_ms': round(row['max_latency_ms'], 2),
                'avg_cost_usd': round(row['avg_cost_usd'], 6)
            }
    
    def get_model_breakdown(self, hours: int = 24) -> List[Dict]:
        """
        Get usage breakdown by model
        
        Args:
            hours: Time window in hours
        
        Returns:
            List of dictionaries with per-model stats
        """
        query = """
            SELECT 
                model,
                COUNT(*) as requests,
                SUM(total_tokens) as tokens,
                SUM(cost_usd) as cost_usd,
                AVG(latency_ms) as avg_latency_ms
            FROM metrics
            WHERE datetime(timestamp) >= datetime('now', '-' || ? || ' hours')
            GROUP BY model
            ORDER BY cost_usd DESC
        """
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, [hours])
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'model': row['model'],
                    'requests': row['requests'],
                    'tokens': row['tokens'],
                    'cost_usd': round(row['cost_usd'], 4),
                    'avg_latency_ms': round(row['avg_latency_ms'], 2)
                })
            
            return results
    
    def clear_old_metrics(self, days: int = 30):
        """
        Delete metrics older than specified days
        
        Args:
            days: Delete metrics older than this many days
        
        Returns:
            Number of deleted entries
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM metrics
                WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days')
            """, [days])
            
            return cursor.rowcount


# Global instance
_metrics_store = None

def get_metrics_store() -> MetricsStore:
    """Get or create global metrics store instance"""
    global _metrics_store
    if _metrics_store is None:
        _metrics_store = MetricsStore()
    return _metrics_store