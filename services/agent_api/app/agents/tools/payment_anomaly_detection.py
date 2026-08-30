"""Strict OpenAI function schemas for payment anomaly detection."""

from typing import Any

DIAGNOSTIC_DIMENSIONS = [
    "merchant",
    "provider",
    "payment_method",
    "country",
    "issuing_bank",
]

FILTER_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "dimension": {"type": "string", "enum": DIAGNOSTIC_DIMENSIONS},
            "value": {"type": "string"},
        },
        "required": ["dimension", "value"],
        "additionalProperties": False,
    },
    "maxItems": 5,
}

PAYMENT_ANOMALY_DETECTION_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_current_window_overview",
        "description": "Get overall acceptance metrics for the latest completed five-minute window and its stored weekday baseline. Call this first.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_current_segment_metrics",
        "description": "Compare the latest completed five-minute window to stored weekday baselines. First scan one dimension at a time with no filters. Only then make a combined-dimension query, retaining a filter supported by a prior result and adding one dimension at a time.",
        "parameters": {
            "type": "object",
            "properties": {
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string", "enum": DIAGNOSTIC_DIMENSIONS},
                    "minItems": 1,
                    "maxItems": 5,
                },
                "filters": FILTER_SCHEMA,
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["dimensions", "filters", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_decline_code_distribution",
        "description": "Show decline-code shares for a previously identified failing segment. Decline codes diagnose a drop; they are not acceptance-rate dimensions.",
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {**FILTER_SCHEMA, "minItems": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["filters", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
