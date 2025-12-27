"""
LangSmith Tracer for Observability
Wraps LangSmith SDK for distributed tracing
"""

import time
import uuid
from typing import Optional, Dict, Any
from contextlib import contextmanager

try:
    from langsmith import Client
    from langsmith.run_helpers import traceable
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None
    traceable = None

from .config import get_config
from .metrics import get_metrics_store
from .cost import CostCalculator


class ObservabilityTracer:
    """
    Distributed tracing and metrics collection
    
    Features:
    - LangSmith integration for distributed tracing
    - Local metrics storage in SQLite
    - Token usage and cost tracking
    - Latency monitoring
    """
    
    def __init__(
        self,
        enabled: bool = True,
        langsmith_enabled: bool = False,
        langsmith_api_key: Optional[str] = None,
        project_name: str = "aider-observability"
    ):
        """
        Initialize tracer
        
        Args:
            enabled: Enable observability
            langsmith_enabled: Enable LangSmith tracing
            langsmith_api_key: LangSmith API key
            project_name: LangSmith project name
        """
        self.enabled = enabled
        self.langsmith_enabled = langsmith_enabled and LANGSMITH_AVAILABLE
        self.project_name = project_name
        
        # Initialize LangSmith client if available
        self.langsmith_client = None
        if self.langsmith_enabled and langsmith_api_key:
            try:
                self.langsmith_client = Client(api_key=langsmith_api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize LangSmith client: {e}")
                self.langsmith_enabled = False
        
        # Initialize metrics store
        self.metrics_store = get_metrics_store() if enabled else None
    
    @contextmanager
    def trace_llm_call(
        self,
        model: str,
        prompt_type: str = "code_generation",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing LLM calls
        
        Usage:
            with tracer.trace_llm_call(model="claude-sonnet-4") as trace:
                # Make LLM call
                response = llm.generate(prompt)
                
                # Log results
                trace.log_result(
                    input_tokens=1000,
                    output_tokens=500,
                    success=True
                )
        
        Args:
            model: Model identifier
            prompt_type: Type of prompt (code_generation, chat, etc.)
            metadata: Additional metadata
        """
        if not self.enabled:
            # If disabled, yield a no-op trace context
            yield TraceContext(enabled=False)
            return
        
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Create trace context
        trace_context = TraceContext(
            enabled=True,
            run_id=run_id,
            model=model,
            prompt_type=prompt_type,
            metadata=metadata or {},
            start_time=start_time,
            tracer=self
        )
        
        # Start LangSmith trace if enabled
        if self.langsmith_enabled and self.langsmith_client:
            try:
                trace_context.langsmith_run = self.langsmith_client.create_run(
                    name=f"aider_{prompt_type}",
                    run_type="llm",
                    inputs={"model": model, "prompt_type": prompt_type},
                    project_name=self.project_name,
                    run_id=run_id
                )
            except Exception as e:
                print(f"Warning: Failed to start LangSmith trace: {e}")
        
        try:
            yield trace_context
        finally:
            # Finalize trace
            trace_context._finalize()
    
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
    ):
        """
        Log a metric entry
        
        This is called automatically by TraceContext.log_result()
        but can also be called directly for custom logging
        """
        if not self.enabled or not self.metrics_store:
            return
        
        self.metrics_store.log_metric(
            run_id=run_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            prompt_type=prompt_type,
            metadata=metadata
        )
    
    def get_statistics(self, hours: int = 24, model: Optional[str] = None) -> Dict:
        """Get aggregated statistics"""
        if not self.enabled or not self.metrics_store:
            return {}
        return self.metrics_store.get_statistics(hours=hours, model=model)
    
    def get_model_breakdown(self, hours: int = 24) -> list:
        """Get usage breakdown by model"""
        if not self.enabled or not self.metrics_store:
            return []
        return self.metrics_store.get_model_breakdown(hours=hours)


class TraceContext:
    """
    Context for a single traced operation
    
    Automatically calculates latency and logs metrics when the context exits
    """
    
    def __init__(
        self,
        enabled: bool,
        run_id: str = "",
        model: str = "",
        prompt_type: str = "",
        metadata: Optional[Dict] = None,
        start_time: float = 0.0,
        tracer: Optional[ObservabilityTracer] = None
    ):
        self.enabled = enabled
        self.run_id = run_id
        self.model = model
        self.prompt_type = prompt_type
        self.metadata = metadata or {}
        self.start_time = start_time
        self.tracer = tracer
        
        # LangSmith run (if enabled)
        self.langsmith_run = None
        
        # Results (set by user)
        self.input_tokens = 0
        self.output_tokens = 0
        self.success = True
        self.error_message = None
        self.logged = False
    
    def log_result(
        self,
        input_tokens: int,
        output_tokens: int,
        success: bool = True,
        error_message: Optional[str] = None,
        additional_metadata: Optional[Dict] = None
    ):
        """
        Log the result of the traced operation
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            success: Whether the operation succeeded
            error_message: Error message if failed
            additional_metadata: Additional metadata to merge
        """
        if not self.enabled:
            return
        
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.success = success
        self.error_message = error_message
        
        # Merge additional metadata
        if additional_metadata:
            self.metadata.update(additional_metadata)
        
        self.logged = True
    
    def _finalize(self):
        """Finalize trace and log metrics"""
        if not self.enabled or not self.logged:
            return
        
        # Calculate latency
        latency_ms = (time.time() - self.start_time) * 1000
        
        # Calculate cost
        cost_usd = CostCalculator.calculate_cost(
            self.model,
            self.input_tokens,
            self.output_tokens
        )
        
        # Log to local metrics store
        if self.tracer:
            self.tracer.log_metric(
                run_id=self.run_id,
                model=self.model,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=self.success,
                error_message=self.error_message,
                prompt_type=self.prompt_type,
                metadata=self.metadata
            )
        
        # Update LangSmith trace if enabled
        if self.langsmith_run and self.tracer and self.tracer.langsmith_client:
            try:
                self.tracer.langsmith_client.update_run(
                    run_id=self.run_id,
                    outputs={
                        "input_tokens": self.input_tokens,
                        "output_tokens": self.output_tokens,
                        "total_tokens": self.input_tokens + self.output_tokens,
                        "cost_usd": cost_usd,
                        "success": self.success
                    },
                    error=self.error_message if not self.success else None,
                    end_time=time.time()
                )
            except Exception as e:
                print(f"Warning: Failed to update LangSmith trace: {e}")


# Global tracer instance
_tracer = None

def get_tracer() -> ObservabilityTracer:
    """Get or create global tracer instance"""
    global _tracer
    if _tracer is None:
        config = get_config()
        _tracer = ObservabilityTracer(
            enabled=config.local_metrics_enabled,
            langsmith_enabled=config.langsmith_enabled,
            langsmith_api_key=config.langsmith_api_key,
            project_name=config.langsmith_project
        )
    return _tracer

def set_tracer(tracer: ObservabilityTracer):
    """Set global tracer instance"""
    global _tracer
    _tracer = tracer