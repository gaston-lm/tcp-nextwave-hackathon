"""Strict function schemas available to ActionTaker."""

from typing import Any

ACTION_TAKER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_merchant_provider_alternatives",
        "description": (
            "Lists payment providers accepted by the incident merchant, excluding the "
            "affected provider. Returns an empty list when the merchant or provider is unknown."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "merchant": {"type": "string", "minLength": 1},
                "affected_provider": {"type": "string", "minLength": 1},
            },
            "required": ["merchant", "affected_provider"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]
