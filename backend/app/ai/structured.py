import json

from pydantic import ValidationError

from app.ai.schemas import StructuredAIResponse


class StructuredOutputError(Exception):
    """Raised when model output is not valid structured data."""


def parse_structured_response(content: str) -> StructuredAIResponse:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(
            "AI returned invalid JSON."
        ) from exc

    try:
        return StructuredAIResponse.model_validate(data)
    except ValidationError as exc:
        raise StructuredOutputError(
            "AI returned JSON that does not match the expected schema."
        ) from exc
