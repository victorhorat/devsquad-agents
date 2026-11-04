from collections import deque
from collections.abc import Callable

from devsquad.llm.base import LLMResponse

Script = str | Callable[[str, str, str], str]


class FakeLLM:
    """LLM roteirizado para testes: devolve respostas pré-definidas em ordem.

    Cada item do script pode ser uma string (conteúdo fixo) ou uma função
    `(system, user, model) -> str` para decidir a resposta dinamicamente.
    """

    def __init__(self, script: list[Script]) -> None:
        self._queue: deque[Script] = deque(script)
        self.calls: list[tuple[str, str, str]] = []

    def complete(self, *, system: str, user: str, model: str) -> LLMResponse:
        self.calls.append((system, user, model))
        if not self._queue:
            raise AssertionError("FakeLLM: script esgotado, mais uma chamada do que esperado")
        item = self._queue.popleft()
        content = item(system, user, model) if callable(item) else item
        return LLMResponse(
            content=content,
            prompt_tokens=len(system) + len(user),
            completion_tokens=len(content),
        )
