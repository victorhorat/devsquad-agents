import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class ResponseParsingError(RuntimeError):
    """O LLM não devolveu um JSON que valide contra o modelo esperado."""


def parse_structured(content: str, model: type[ModelT]) -> ModelT:
    """Extrai e valida JSON da resposta de um LLM, tolerando texto em volta.

    Nem todo provedor compatível com OpenAI suporta `response_format`, então o
    conteúdo pode vir com markdown, texto explicativo, etc. Tentamos, em ordem:
    1. parsear o conteúdo inteiro como JSON;
    2. extrair o maior bloco `{...}` do texto e parsear isso.
    """
    for candidate in (content, _extract_json_block(content)):
        if candidate is None:
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            last_error = exc
            continue
    raise ResponseParsingError(
        f"Não foi possível extrair um {model.__name__} válido da resposta do LLM: {content[:500]!r}"
    ) from locals().get("last_error")


def _extract_json_block(content: str) -> str | None:
    match = _JSON_BLOCK_RE.search(content)
    return match.group(0) if match else None
