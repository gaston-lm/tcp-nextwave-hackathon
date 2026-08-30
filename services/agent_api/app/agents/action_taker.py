"""Bounded action planner for a persisted newly-created incident."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from ..incidents import IncidentRepository
from ..models import ActionableIncident, ActionProposal, ActionTakerResult
from ..observability import traced_agent
from ..settings import Settings, get_settings
from ..structured_output import parse_output, response_format
from .prompts import ACTION_TAKER_INSTRUCTIONS
from .tools import ACTION_TAKER_TOOLS


class ActionTaker:
    def __init__(
        self, repository: IncidentRepository, settings: Settings | None = None
    ) -> None:
        settings = settings or get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.repository = repository
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.model = settings.openai_model

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "get_merchant_provider_alternatives":
            return await self.repository.provider_alternatives(
                arguments["merchant"], arguments["affected_provider"]
            )
        raise ValueError(f"Unsupported tool: {name}")

    @traced_agent("action_taker")
    async def decide(
        self, incident: ActionableIncident, max_steps: int
    ) -> ActionTakerResult:
        response = await self.client.responses.create(
            model=self.model,
            instructions=ACTION_TAKER_INSTRUCTIONS,
            input=json.dumps(incident.model_dump(mode="json")),
            tools=ACTION_TAKER_TOOLS,
            text=response_format("incident_action", ActionProposal),
            tool_choice="auto",
            parallel_tool_calls=False,
            reasoning={"effort": "low"},
            store=True,
        )
        for step in range(1, max_steps + 1):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                proposal = parse_output(ActionProposal, response.output_text)
                alternatives = await self._provider_alternatives(incident)
                self.validate_proposal(incident, proposal, alternatives)
                return ActionTakerResult(result=proposal, steps_used=step - 1)
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
                instructions=ACTION_TAKER_INSTRUCTIONS,
                previous_response_id=response.id,
                input=outputs,
                tools=ACTION_TAKER_TOOLS,
                text=response_format("incident_action", ActionProposal),
                tool_choice="auto",
                parallel_tool_calls=False,
                reasoning={"effort": "low"},
                store=True,
            )
        raise ValueError("ActionTaker exceeded the configured tool-step limit")

    async def _provider_alternatives(self, incident: ActionableIncident) -> list[str]:
        signature = incident.dimension_signatures
        if signature.merchant is None or signature.provider is None:
            return []
        rows = await self.repository.provider_alternatives(
            signature.merchant, signature.provider
        )
        return [row["provider"] for row in rows]

    @staticmethod
    def validate_proposal(
        incident: ActionableIncident,
        proposal: ActionProposal,
        provider_alternatives: list[str],
    ) -> None:
        if proposal.incident_id != incident.incident_id:
            raise ValueError("ActionTaker returned an action for another incident")
        if incident.related_deployment_ids:
            if proposal.action_type != "deploy_rollback":
                raise ValueError(
                    "Deployment-linked incidents require rollback guidance"
                )
            if not any(
                deploy_id in proposal.action_details
                for deploy_id in incident.related_deployment_ids
            ):
                raise ValueError("Rollback guidance must identify a related deployment")
            return
        if provider_alternatives:
            if proposal.action_type != "recommend_switch_provider_to_merchant":
                raise ValueError(
                    "Provider incidents with alternatives require a switch"
                )
            if not any(
                provider in proposal.action_details
                for provider in provider_alternatives
            ):
                raise ValueError("Provider guidance must name an approved alternative")
            return
        if proposal.action_type != "post_slack_alert_to_channel":
            raise ValueError(
                "Incidents without alternatives require a Slack alert draft"
            )
