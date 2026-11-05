from types import SimpleNamespace

import pytest

from devsquad.llm.openai_client import OpenAICompatibleClient, TruncatedResponseError


def _fake_response(content: str, finish_reason: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20)
    return SimpleNamespace(choices=[choice], usage=usage)


def _client_with_fake_create(fake_create):
    client = OpenAICompatibleClient(base_url="http://localhost:9", api_key="dummy")
    client._client.chat.completions.create = fake_create
    return client


def test_complete_returns_content_on_normal_finish():
    client = _client_with_fake_create(lambda **kwargs: _fake_response("ola", finish_reason="stop"))
    response = client.complete(system="s", user="u", model="m")
    assert response.content == "ola"
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 20


def test_complete_raises_on_truncated_finish_reason():
    client = _client_with_fake_create(
        lambda **kwargs: _fake_response("codigo cortado...", finish_reason="length")
    )
    with pytest.raises(TruncatedResponseError):
        client.complete(system="s", user="u", model="m")


def test_complete_passes_configured_max_output_tokens():
    captured_kwargs = {}

    def fake_create(**kwargs):
        captured_kwargs.update(kwargs)
        return _fake_response("ok", finish_reason="stop")

    client = OpenAICompatibleClient(
        base_url="http://localhost:9", api_key="dummy", max_output_tokens=123
    )
    client._client.chat.completions.create = fake_create
    client.complete(system="s", user="u", model="m")

    assert captured_kwargs["max_tokens"] == 123
