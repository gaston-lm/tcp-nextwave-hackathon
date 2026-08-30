"""Helpers for OpenAI Responses API Structured Outputs."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)


class AgentOutputValidationError(ValueError):
    """Raised when a model does not return the contract promised by its schema."""


def response_format(name: str, model: type[BaseModel]) -> dict[str, object]:
    return {
        "format": {
            "type": "json_schema",
            "name": name,
            "strict": True,
            "schema": model.model_json_schema(),
        }
    }


def parse_output(model: type[Model], output_text: str) -> Model:
    try:
        return model.model_validate(json.loads(output_text))
    except (json.JSONDecodeError, ValidationError) as error:
        raise AgentOutputValidationError(
            f"Model response did not satisfy the {model.__name__} schema: {error}"
        ) from error
