import time

import openai

from devsquad.llm.base import LLMResponse

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.5


class LLMConfigError(RuntimeError):
    """Configuração de provedor ausente ou inválida."""


class OpenAICompatibleClient:
    """Cliente genérico para qualquer endpoint compatível com a API da OpenAI.

    base_url é livre (Gemini, Groq, OpenRouter, DeepSeek, Ollama, ou qualquer
    outro endpoint OpenAI-compatible que o usuário configure via env var).
    """

    def __init__(self, *, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        if not base_url or not api_key:
            raise LLMConfigError(
                "LLM_BASE_URL e LLM_API_KEY precisam estar configurados (veja .env.example)."
            )
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    def complete(self, *, system: str, user: str, model: str) -> LLMResponse:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                choice = response.choices[0].message.content or ""
                usage = response.usage
                return LLMResponse(
                    content=choice,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                )
            except openai.APIStatusError as exc:
                last_error = exc
                if exc.status_code not in RETRYABLE_STATUS_CODES or attempt == MAX_RETRIES:
                    raise
                time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                last_error = exc
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
        raise last_error  # pragma: no cover - loop sempre retorna ou levanta antes
