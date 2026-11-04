from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int


class LLMClient(Protocol):
    """Interface mínima que Refiner/Coder/QA usam para falar com qualquer provedor."""

    def complete(self, *, system: str, user: str, model: str) -> LLMResponse: ...
