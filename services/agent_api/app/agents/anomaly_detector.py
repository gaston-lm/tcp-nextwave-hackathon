"""Bounded ReAct agent that compares current payments with their baseline."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from ..metrics import MetricsService
from ..observability import traced_agent
from ..settings import Settings, get_settings
from ..models import PaymentAnomalyDetectionResult
from .prompts import PAYMENT_ANOMALY_DETECTION_INSTRUCTIONS
from .tools import PAYMENT_ANOMALY_DETECTION_TOOLS


class AnomalyDetector:
    def __init__(self, metrics: MetricsService, settings: Settings | None = None) -> None:
        self.metrics = metrics
        settings = settings or get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.model = settings.openai_model

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "get_current_segment_metrics":
            dimensions = arguments.get("dimensions", [])
            filters = arguments.get("filters", [])
            if len(dimensions) > 1 and not filters:
                raise ValueError(
                    "Unfiltered multi-dimension scans are not allowed. "
                    "First query exactly one dimension with no filters, then retain "
                    "an evidence-backed filter while adding one dimension."
                )
        if "filters" in arguments:
            arguments["filters"] = {
                item["dimension"]: item["value"] for item in arguments["filters"]
            }
        if name == "get_current_window_overview":
            return await self.metrics.overview()
        if name == "get_current_segment_metrics":
            return await self.metrics.segment_metrics(**arguments)
        if name == "get_decline_code_distribution":
            return await self.metrics.decline_code_distribution(**arguments)
        raise ValueError(f"Unsupported tool: {name}")

    @traced_agent("anomaly_detector")
    async def detect(self, max_steps: int) -> PaymentAnomalyDetectionResult:
        response = await self.client.responses.create(
            model=self.model,
            instructions=PAYMENT_ANOMALY_DETECTION_INSTRUCTIONS,
            input="Investigate the latest completed five-minute window. Begin with the overview.",
            tools=PAYMENT_ANOMALY_DETECTION_TOOLS,
            # The first observation is mandatory and deterministic. Subsequent
            # calls remain ReAct decisions made from the returned evidence.
            tool_choice={"type": "function", "name": "get_current_window_overview"},
            parallel_tool_calls=False,
            reasoning={"effort": "low"},
            # The next step uses previous_response_id, which requires OpenAI to
            # retain the response state for the duration of the tool loop.
            store=True,
        )
        for step in range(1, max_steps + 1):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                return PaymentAnomalyDetectionResult(
                    result=response.output_text,
                    steps_used=step - 1,
                )
            outputs = []
            for call in calls:
                try:
                    result = await self._call_tool(call.name, json.loads(call.arguments))
                except (ValueError, json.JSONDecodeError) as error:
                    result = {"error": str(error)}
                outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result, default=str)})
            response = await self.client.responses.create(
                model=self.model,
                instructions=PAYMENT_ANOMALY_DETECTION_INSTRUCTIONS,
                previous_response_id=response.id,
                input=outputs,
                tools=PAYMENT_ANOMALY_DETECTION_TOOLS,
                tool_choice="auto",
                parallel_tool_calls=False,
                reasoning={"effort": "low"},
                store=True,
            )
        return PaymentAnomalyDetectionResult(
            result=json.dumps(
                {
                    "investigation_status": "incomplete",
                    "summary": "Investigation reached its tool-call limit.",
                }
            ),
            steps_used=max_steps,
        )
