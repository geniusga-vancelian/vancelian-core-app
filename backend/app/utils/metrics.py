"""
Prometheus metrics for observability
"""

import time
from typing import Optional
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry

# Create a custom registry to avoid conflicts
metrics_registry = CollectorRegistry()

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status"],
    registry=metrics_registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["path", "method"],
    registry=metrics_registry,
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Webhook metrics
zand_webhook_received_total = Counter(
    "zand_webhook_received_total",
    "Total ZAND webhook requests received",
    registry=metrics_registry,
)

zand_webhook_rejected_total = Counter(
    "zand_webhook_rejected_total",
    "Total ZAND webhook requests rejected",
    ["reason"],  # signature_invalid, timestamp_invalid, duplicate, etc.
    registry=metrics_registry,
)

# Rate limiting metrics
rate_limited_total = Counter(
    "rate_limited_total",
    "Total requests rate limited",
    ["group"],  # webhook, admin, api
    registry=metrics_registry,
)

# Ledger metrics
ledger_invariant_violations_total = Counter(
    "ledger_invariant_violations_total",
    "Total ledger invariant violations detected",
    registry=metrics_registry,
)

# Compliance metrics
compliance_actions_total = Counter(
    "compliance_actions_total",
    "Total compliance actions",
    ["action"],  # release_funds, reject_deposit
    registry=metrics_registry,
)

# Investment metrics
investment_actions_total = Counter(
    "investment_actions_total",
    "Total investment actions",
    registry=metrics_registry,
)


def record_http_request(
    path: str,
    method: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """
    Record HTTP request metrics.
    
    Args:
        path: Request path (normalized)
        method: HTTP method
        status_code: Response status code
        duration_seconds: Request duration in seconds
    """
    # Normalize path (remove UUIDs and IDs for better aggregation)
    normalized_path = _normalize_path(path)
    
    http_requests_total.labels(
        path=normalized_path,
        method=method.upper(),
        status=str(status_code),
    ).inc()
    
    http_request_duration_seconds.labels(
        path=normalized_path,
        method=method.upper(),
    ).observe(duration_seconds)


def record_webhook_received() -> None:
    """Record webhook received"""
    zand_webhook_received_total.inc()


def record_webhook_rejected(reason: str) -> None:
    """
    Record webhook rejection.
    
    Args:
        reason: Rejection reason (signature_invalid, timestamp_invalid, duplicate, etc.)
    """
    zand_webhook_rejected_total.labels(reason=reason).inc()


def record_rate_limit_exceeded(group: str) -> None:
    """
    Record rate limit exceeded.
    
    Args:
        group: Endpoint group (webhook, admin, api)
    """
    rate_limited_total.labels(group=group).inc()


def record_ledger_invariant_violation() -> None:
    """Record ledger invariant violation"""
    ledger_invariant_violations_total.inc()


def record_compliance_action(action: str) -> None:
    """
    Record compliance action.
    
    Args:
        action: Action type (release_funds, reject_deposit)
    """
    compliance_actions_total.labels(action=action).inc()


def record_investment_action() -> None:
    """Record investment action"""
    investment_actions_total.inc()


def _normalize_path(path: str) -> str:
    """
    Normalize path for metrics (replace UUIDs and IDs with placeholders).
    
    Examples:
        /api/v1/wallet -> /api/v1/wallet
        /api/v1/transactions/123e4567-... -> /api/v1/transactions/{id}
        /admin/v1/compliance/release-funds -> /admin/v1/compliance/release-funds
    """
    import re
    
    # Replace UUIDs
    path = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '{id}',
        path,
        flags=re.IGNORECASE,
    )
    
    # Replace numeric IDs (if any remain)
    path = re.sub(r'/\d+', '/{id}', path)
    
    return path


def get_metrics_output() -> bytes:
    """Get Prometheus metrics output"""
    return generate_latest(metrics_registry)

