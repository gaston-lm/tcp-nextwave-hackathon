"""Strict function schemas available to IncidentReviewer."""

from typing import Any

INCIDENT_REVIEWER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_closed_incidents",
        "description": "Semantic search over closed incidents older than 24 hours.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_recent_deploys",
        "description": "Semantic search over payment processor deployment logs.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
