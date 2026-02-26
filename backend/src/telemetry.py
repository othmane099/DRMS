from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config import settings

logger = logging.getLogger(__name__)


def setup_telemetry(app=None) -> None:  # type: ignore[no-untyped-def]
    if not settings.OTEL_ENABLED:
        return

    resource = Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME})

    exporter = OTLPSpanExporter(
        endpoint=f"{settings.OTEL_ENDPOINT.rstrip('/')}/v1/traces",
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    from db import engine as db_engine

    SQLAlchemyInstrumentor().instrument(
        engine=db_engine.sync_engine, capture_parameters=True
    )

    HTTPXClientInstrumentor().instrument()

    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    logger.info(
        "OpenTelemetry tracing enabled (service=%s, endpoint=%s)",
        settings.OTEL_SERVICE_NAME,
        settings.OTEL_ENDPOINT,
    )
