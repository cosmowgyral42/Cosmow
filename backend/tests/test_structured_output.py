import pytest

from app.ai.structured import (
    StructuredOutputError,
    parse_structured_response,
)


def test_valid_structured_response():
    result = parse_structured_response(
        '{"answer": "COSMOW is ready.", "confidence": 0.95}'
    )

    assert result.answer == "COSMOW is ready."
    assert result.confidence == 0.95


def test_invalid_json_is_rejected():
    with pytest.raises(
        StructuredOutputError,
        match="invalid JSON",
    ):
        parse_structured_response(
            "This is not JSON."
        )


def test_missing_required_field_is_rejected():
    with pytest.raises(
        StructuredOutputError,
        match="does not match",
    ):
        parse_structured_response(
            '{"confidence": 0.8}'
        )


def test_invalid_confidence_is_rejected():
    with pytest.raises(
        StructuredOutputError,
        match="does not match",
    ):
        parse_structured_response(
            '{"answer": "Test", "confidence": 2.0}'
        )


def test_empty_answer_is_rejected():
    with pytest.raises(
        StructuredOutputError,
        match="does not match",
    ):
        parse_structured_response(
            '{"answer": "", "confidence": 0.8}'
        )
