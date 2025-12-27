"""
Observability Module for Aider
Provides distributed tracing, metrics collection, and cost tracking
"""

from .tracer import ObservabilityTracer, TraceContext, get_tracer, set_tracer
from .metrics import MetricsStore, MetricEntry, get_metrics_store
from .cost import CostCalculator, calculate_cost
from .config import ObservabilityConfig, get_config, set_config

__all__ = [
    # Tracer
    'ObservabilityTracer',
    'TraceContext',
    'get_tracer',
    'set_tracer',
    
    # Metrics
    'MetricsStore',
    'MetricEntry',
    'get_metrics_store',
    
    # Cost
    'CostCalculator',
    'calculate_cost',
    
    # Config
    'ObservabilityConfig',
    'get_config',
    'set_config',
]

__version__ = '1.0.0'