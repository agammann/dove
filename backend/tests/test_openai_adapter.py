"""Exercise the real SDK and schemas through an in-memory, synthetic transport."""

import json

import httpx
import openai
import pytest
from dove import providers
from dove.config import settings
from pydantic import ValidationError


def mock_client(monkeypatch, content):
    requests = []
    real_client = openai.OpenAI

    def handle(request):
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path == "/v1/responses"
        assert request.headers["authorization"] == "Bearer synthetic-test-key"
        return httpx.Response(
            200,
            json={
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 0,
                "model": "synthetic-model",
                "status": "completed",
                "output": [{"id": "msg_synthetic", "type": "message", "role": "assistant", "status": "completed", "content": content}],
                "usage": {"input_tokens": 12, "output_tokens": 7, "total_tokens": 19},
            },
        )

    transport = httpx.Client(transport=httpx.MockTransport(handle))
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: real_client(http_client=transport, **kwargs))
    monkeypatch.setattr(settings, "model_adapter", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "synthetic-test-key")
    monkeypatch.setattr(settings, "openai_model", "synthetic-model")
    return requests


@pytest.mark.parametrize("task", ["analyze", "draft", "reply"])
def test_real_sdk_parses_synthetic_structured_results(monkeypatch, task):
    payloads = {
        "analyze": {"requirements": [{"category": "amount", "title": "Amount", "status": "received", "source": {"document_id": "doc-synthetic", "version": 1, "page": 1, "excerpt": "USD 42.00", "value": "42.00"}}]},
        "draft": {"body": "Please provide the synthetic purchase order."},
        "reply": {"classification": "relevant", "associations": [{"requirement_id": "req-synthetic", "excerpt": "PO-123"}], "explanation": "Review the synthetic reply."},
    }
    requests = mock_client(monkeypatch, [{"type": "output_text", "text": json.dumps(payloads[task]), "annotations": []}])
    if task == "analyze":
        result, usage = providers.analyze([{"id": "doc-synthetic", "version": 1, "pages": ["USD 42.00"]}])
    elif task == "draft":
        result, usage = providers.draft_request("Synthetic work", [{"title": "Purchase order"}])
    else:
        result, usage = providers.interpret_reply("PO-123", [{"id": "req-synthetic", "title": "Purchase order"}])
    assert result.model_dump() == payloads[task]
    assert usage == {"adapter": "openai", "simulated": False, "input_tokens": 12, "output_tokens": 7}
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["input"][1]["role"] == "user"


def test_real_sdk_rejects_invalid_structured_result(monkeypatch):
    mock_client(monkeypatch, [{"type": "output_text", "text": '{"body":""}', "annotations": []}])
    with pytest.raises(ValidationError):
        providers.draft_request("Synthetic work", [{"title": "Purchase order"}])


def test_real_sdk_refusal_does_not_become_a_result(monkeypatch):
    mock_client(monkeypatch, [{"type": "refusal", "refusal": "Synthetic refusal"}])
    with pytest.raises(ValueError, match="could not be validated"):
        providers.draft_request("Synthetic work", [{"title": "Purchase order"}])
