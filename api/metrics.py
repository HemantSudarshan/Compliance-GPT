"""
metrics.py - Prometheus Metrics for ComplianceGPT

Provides observability metrics for production monitoring.
"""

import time
from functools import wraps
from typing import Callable
from dataclasses import dataclass, field
from collections import defaultdict
import threading


@dataclass
class MetricValue:
    """Holds a metric value with labels."""
    value: float = 0.0
    labels: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """Prometheus-style counter metric."""
    
    def __init__(self, name: str, description: str, labels: list[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def inc(self, value: float = 1, **labels):
        """Increment the counter."""
        key = tuple(labels.get(label_name, "") for label_name in self.label_names)
        with self._lock:
            self._values[key] += value
    
    def get(self, **labels) -> float:
        """Get current counter value."""
        key = tuple(labels.get(label_name, "") for label_name in self.label_names)
        return self._values.get(key, 0.0)
    
    def collect(self) -> list[dict]:
        """Collect all metric values."""
        results = []
        for key, value in self._values.items():
            labels = dict(zip(self.label_names, key))
            results.append({"labels": labels, "value": value})
        return results


class Gauge:
    """Prometheus-style gauge metric."""
    
    def __init__(self, name: str, description: str, labels: list[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def set(self, value: float, **labels):
        """Set the gauge value."""
        key = tuple(labels.get(label_name, "") for label_name in self.label_names)
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1, **labels):
        """Increment the gauge."""
        key = tuple(labels.get(label_name, "") for label_name in self.label_names)
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def dec(self, value: float = 1, **labels):
        """Decrement the gauge."""
        self.inc(-value, **labels)
    
    def get(self, **labels) -> float:
        """Get current gauge value."""
        key = tuple(labels.get(label_name, "") for label_name in self.label_names)
        return self._values.get(key, 0.0)
    
    def collect(self) -> list[dict]:
        """Collect all metric values."""
        results = []
        for key, value in self._values.items():
            labels = dict(zip(self.label_names, key))
            results.append({"labels": labels, "value": value})
        return results


class Histogram:
    """Prometheus-style histogram metric."""
    
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
    
    def __init__(self, name: str, description: str, labels: list[str] = None, buckets: tuple = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._counts: dict[tuple, dict] = defaultdict(lambda: defaultdict(int))
        self._sums: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
    
    def observe(self, value: float, **labels):
        """Record an observation."""
        key = tuple(labels.get(label_name, "") for label_name in self.label_names)
        with self._lock:
            self._sums[key] += value
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[key][bucket] += 1
            self._counts[key][float('inf')] += 1  # +Inf bucket
    
    def collect(self) -> list[dict]:
        """Collect all metric values."""
        results = []
        for key in self._counts.keys():
            labels = dict(zip(self.label_names, key))
            results.append({
                "labels": labels,
                "buckets": dict(self._counts[key]),
                "sum": self._sums[key],
                "count": self._counts[key][float('inf')]
            })
        return results


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, histogram: Histogram, **labels):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        duration = time.time() - self.start_time
        self.histogram.observe(duration, **self.labels)


# =============================================================================
# Application Metrics
# =============================================================================

class ComplianceGPTMetrics:
    """Central metrics registry for ComplianceGPT."""
    
    def __init__(self):
        # Request metrics
        self.requests_total = Counter(
            "compliancegpt_requests_total",
            "Total number of requests",
            labels=["method", "endpoint", "status"]
        )
        
        self.request_duration = Histogram(
            "compliancegpt_request_duration_seconds",
            "Request duration in seconds",
            labels=["method", "endpoint"],
            buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10)
        )
        
        # Query metrics
        self.queries_total = Counter(
            "compliancegpt_queries_total",
            "Total compliance queries",
            labels=["regulation", "has_context"]
        )
        
        self.query_duration = Histogram(
            "compliancegpt_query_duration_seconds",
            "Query processing duration",
            labels=["regulation", "provider"]
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            "compliancegpt_cache_hits_total",
            "Cache hit count"
        )
        
        self.cache_misses = Counter(
            "compliancegpt_cache_misses_total",
            "Cache miss count"
        )
        
        self.cache_size = Gauge(
            "compliancegpt_cache_size",
            "Current cache size"
        )
        
        # LLM metrics
        self.llm_requests = Counter(
            "compliancegpt_llm_requests_total",
            "LLM API requests",
            labels=["provider", "model", "status"]
        )
        
        self.llm_tokens = Counter(
            "compliancegpt_llm_tokens_total",
            "LLM tokens used",
            labels=["provider", "type"]  # type: input/output
        )
        
        # Weaviate metrics
        self.weaviate_queries = Counter(
            "compliancegpt_weaviate_queries_total",
            "Weaviate search queries",
            labels=["status"]
        )
        
        self.chunks_retrieved = Histogram(
            "compliancegpt_chunks_retrieved",
            "Number of chunks retrieved per query",
            buckets=(1, 2, 3, 4, 5, 7, 10, 15, 20)
        )
        
        # System metrics
        self.active_connections = Gauge(
            "compliancegpt_active_connections",
            "Current active connections"
        )
        
        self.rate_limit_exceeded = Counter(
            "compliancegpt_rate_limit_exceeded_total",
            "Rate limit exceeded count",
            labels=["client_ip"]
        )
        
        # Error metrics
        self.errors_total = Counter(
            "compliancegpt_errors_total",
            "Total errors",
            labels=["type", "endpoint"]
        )
    
    def format_prometheus(self) -> str:
        """Format all metrics in Prometheus exposition format."""
        lines = []
        
        # Helper to format metric
        def format_metric(metric, metric_type: str):
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} {metric_type}")
            
            for item in metric.collect():
                labels = item.get("labels", {})
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                
                if metric_type == "histogram":
                    # Format histogram buckets
                    for bucket, count in sorted(item.get("buckets", {}).items()):
                        bucket_label = f'{label_str},le="{bucket}"' if label_str else f'le="{bucket}"'
                        lines.append(f"{metric.name}_bucket{{{bucket_label}}} {count}")
                    
                    sum_labels = f"{{{label_str}}}" if label_str else ""
                    lines.append(f"{metric.name}_sum{sum_labels} {item.get('sum', 0)}")
                    lines.append(f"{metric.name}_count{sum_labels} {item.get('count', 0)}")
                else:
                    label_part = f"{{{label_str}}}" if label_str else ""
                    lines.append(f"{metric.name}{label_part} {item.get('value', 0)}")
            
            lines.append("")
        
        # Format all metrics
        format_metric(self.requests_total, "counter")
        format_metric(self.request_duration, "histogram")
        format_metric(self.queries_total, "counter")
        format_metric(self.query_duration, "histogram")
        format_metric(self.cache_hits, "counter")
        format_metric(self.cache_misses, "counter")
        format_metric(self.cache_size, "gauge")
        format_metric(self.llm_requests, "counter")
        format_metric(self.llm_tokens, "counter")
        format_metric(self.weaviate_queries, "counter")
        format_metric(self.chunks_retrieved, "histogram")
        format_metric(self.active_connections, "gauge")
        format_metric(self.rate_limit_exceeded, "counter")
        format_metric(self.errors_total, "counter")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Export metrics as dictionary."""
        return {
            "requests": {
                "total": sum(v for v in self.requests_total._values.values()),
                "by_endpoint": dict(self.requests_total._values)
            },
            "queries": {
                "total": sum(v for v in self.queries_total._values.values()),
            },
            "cache": {
                "hits": self.cache_hits.get(),
                "misses": self.cache_misses.get(),
                "size": self.cache_size.get(),
                "hit_rate": self._calc_hit_rate()
            },
            "llm": {
                "requests": sum(v for v in self.llm_requests._values.values()),
            },
            "errors": {
                "total": sum(v for v in self.errors_total._values.values())
            }
        }
    
    def _calc_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        hits = self.cache_hits.get()
        misses = self.cache_misses.get()
        total = hits + misses
        return hits / total if total > 0 else 0.0


# Global metrics instance
metrics = ComplianceGPTMetrics()


# Decorator for timing functions
def timed(histogram: Histogram, **labels):
    """Decorator to time function execution."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with Timer(histogram, **labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator
