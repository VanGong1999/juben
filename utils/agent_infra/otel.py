"""
可选 OpenTelemetry 追踪 — 未安装时退化为 no-op
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

_tracer = None
_checked = False


def _get_tracer():
    global _tracer, _checked
    if _checked:
        return _tracer
    _checked = True
    try:
        from opentelemetry import trace

        _tracer = trace.get_tracer("juben.agent_infra")
    except ImportError:
        _tracer = None
        logger.debug("opentelemetry not installed; otel spans disabled")
    return _tracer


@contextmanager
def otel_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[Any]:
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span(name) as span:
        if attributes and span is not None:
            for k, v in attributes.items():
                try:
                    span.set_attribute(k, v)
                except Exception:
                    pass
        yield span


def configure_otel_from_env() -> bool:
    """
    若设置了 OTEL_EXPORTER_OTLP_ENDPOINT 则尝试配置 OTLP exporter。
    """
    import os

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": "juben-agent-infra"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        global _tracer, _checked
        _checked = False
        _tracer = None
        logger.info("OpenTelemetry configured: %s", endpoint)
        return True
    except Exception:
        logger.warning("OpenTelemetry configure failed", exc_info=True)
        return False
