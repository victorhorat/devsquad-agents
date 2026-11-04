import pytest

from devsquad.llm.fake import FakeLLM


def test_returns_scripted_responses_in_order():
    fake = FakeLLM(["primeira", "segunda"])
    first = fake.complete(system="s", user="u1", model="m")
    second = fake.complete(system="s", user="u2", model="m")
    assert first.content == "primeira"
    assert second.content == "segunda"
    assert len(fake.calls) == 2


def test_supports_callable_script_items():
    fake = FakeLLM([lambda system, user, model: f"echo:{user}"])
    response = fake.complete(system="s", user="oi", model="m")
    assert response.content == "echo:oi"


def test_raises_when_script_exhausted():
    fake = FakeLLM(["unica"])
    fake.complete(system="s", user="u", model="m")
    with pytest.raises(AssertionError):
        fake.complete(system="s", user="u", model="m")
