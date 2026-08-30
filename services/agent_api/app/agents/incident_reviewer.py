"""Bounded reviewer that proposes new or updated payment incidents."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from ..incidents import IncidentRepository
from ..models import (
    AnomalyInvestigation,
    IncidentReviewDecision,
    IncidentReviewerResult,
    RecentIncident,
)
from ..observability import traced_agent
from ..settings import Settings, get_settings
from ..structured_output import parse_output, response_format
from .prompts import INCIDENT_REVIEWER_INSTRUCTIONS
from .tools import INCIDENT_REVIEWER_TOOLS


class IncidentReviewer:
    def __init__(
        self, repository: IncidentRepository, settings: Settings | None = None
    ) -> None:
        settings = settings or get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.repository = repository
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.model = settings.openai_model

    async def _embedding(self, query: str) -> list[float]:
        response = await self.client.embeddings.create(
            model="text-embedding-3-small", input=query
        )
        return response.data[0].embedding

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        embedding = await self._embedding(arguments["query"])
        if name == "search_closed_incidents":
            return await self.repository.search_closed_incidents(
                embedding, arguments["limit"]
            )
        if name == "search_recent_deploys":
            return await self.repository.search_deployments(
                embedding, arguments["limit"]
            )
        raise ValueError(f"Unsupported tool: {name}")

    @traced_agent("incident_reviewer")
    async def review(
        self,
        investigation: AnomalyInvestigation,
        recent_incidents: list[RecentIncident],
        max_steps: int,
    ) -> IncidentReviewerResult:
        payload = {
            "anomaly_investigation": investigation.model_dump(mode="json"),
            "recent_open_incidents": [
                item.model_dump(mode="json") for item in recent_incidents
            ],
        }
        response = await self.client.responses.create(
            model=self.model,
            instructions=INCIDENT_REVIEWER_INSTRUCTIONS,
            input=json.dumps(payload),
            tools=INCIDENT_REVIEWER_TOOLS,
            text=response_format("incident_review", IncidentReviewDecision),
            tool_choice="auto",
            parallel_tool_calls=False,
            reasoning={"effort": "low"},
            store=True,
        )
        for step in range(1, max_steps + 1):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                decision = parse_output(IncidentReviewDecision, response.output_text)
                recent_ids = {item.incident_id for item in recent_incidents}
                invalid_ids = {
                    proposal.incident_id
                    for proposal in decision.updated_incidents
                    if proposal.incident_id not in recent_ids
                }
                if invalid_ids:
                    raise ValueError(
                        "Reviewer proposed updates outside the supplied 24-hour context: "
                        f"{sorted(invalid_ids)}"
                    )
                return IncidentReviewerResult(result=decision, steps_used=step - 1)
            outputs = []
            for call in calls:
                try:
                    result = await self._call_tool(
                        call.name, json.loads(call.arguments)
                    )
                except (KeyError, ValueError, json.JSONDecodeError) as error:
                    result = {"error": str(error)}
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, default=str),
                    }
                )
            response = await self.client.responses.create(
                model=self.model,
                instructions=INCIDENT_REVIEWER_INSTRUCTIONS,
                previous_response_id=response.id,
                input=outputs,
                tools=INCIDENT_REVIEWER_TOOLS,
                text=response_format("incident_review", IncidentReviewDecision),
                tool_choice="auto",
                parallel_tool_calls=False,
                reasoning={"effort": "low"},
                store=True,
            )
        return IncidentReviewerResult(
            result=IncidentReviewDecision(new_incidents=[], updated_incidents=[]),
            steps_used=max_steps,
        )
