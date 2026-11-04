import os

from devsquad.config import Settings


def test_defaults_without_env(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.llm_model == "gemini-2.0-flash"
    assert settings.max_iterations == 3


def test_model_for_falls_back_to_llm_model():
    settings = Settings(_env_file=None, llm_model="base-model")
    assert settings.model_for("coder") == "base-model"


def test_model_for_uses_override():
    settings = Settings(_env_file=None, llm_model="base-model", coder_model="coder-special")
    assert settings.model_for("coder") == "coder-special"


def test_env_vars_override(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "from-env")
    settings = Settings(_env_file=None)
    assert settings.llm_model == "from-env"
    assert os.environ["LLM_MODEL"] == "from-env"
