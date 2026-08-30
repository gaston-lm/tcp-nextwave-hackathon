"""Optional Arize AX tracing for the agent, tools, and OpenAI client."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from arize.otel import register
from openinference.instrumentation import OITracer, TraceConfig
from openinference.instrumentation.openai import OpenAIInstrumentor

from .settings import Settings, get_settings

logger = logging.getLogger(__name__)
Function = TypeVar("Function", bound=Callable[..., Any])


def _configure_tracing(settings: Settings) -> OITracer | None:
    if not all(
        [
            settings.arize_space_id,
            settings.arize_api_key,
            settings.arize_project_name,
            settings.arize_collector_endpoint,
        ]
    ):
        logger.info("Arize AX tracing is disabled: Arize configuration is incomplete.")
        return None

    tracer_provider = register(
        space_id=settings.arize_space_id,
        api_key=settings.arize_api_key.get_secret_value(),
        project_name=settings.arize_project_name,
        endpoint=settings.arize_collector_endpoint,
    )
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info(
        "Arize AX tracing initialized for project %s.", settings.arize_project_name
    )
    return OITracer(tracer_provider.get_tracer(__name__), config=TraceConfig())


TRACER = _configure_tracing(get_settings())


def traced_agent(name: str) -> Callable[[Function], Function]:
    """Decorate an agent boundary only when Arize AX is configured."""
    if TRACER is None:
        return lambda function: function
    return TRACER.agent(name=name)


def traced_chain(name: str) -> Callable[[Function], Function]:
    """Decorate an orchestration boundary only when Arize AX is configured."""
    if TRACER is None:
        return lambda function: function
    return TRACER.chain(name=name)


def traced_tool(name: str, description: str) -> Callable[[Function], Function]:
    """Decorate a local tool execution only when Arize AX is configured."""
    if TRACER is None:
        return lambda function: function
    return TRACER.tool(name=name, description=description)
