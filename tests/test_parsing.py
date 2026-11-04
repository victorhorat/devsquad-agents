import pytest
from pydantic import BaseModel

from devsquad.parsing import ResponseParsingError, parse_structured


class Dummy(BaseModel):
    ok: bool
    note: str


def test_parses_pure_json():
    result = parse_structured('{"ok": true, "note": "tudo bem"}', Dummy)
    assert result.ok is True
    assert result.note == "tudo bem"


def test_parses_json_wrapped_in_markdown_and_text():
    content = 'Aqui está a análise:\n```json\n{"ok": false, "note": "falhou"}\n```\nFim.'
    result = parse_structured(content, Dummy)
    assert result.ok is False
    assert result.note == "falhou"


def test_raises_when_no_valid_json():
    with pytest.raises(ResponseParsingError):
        parse_structured("isso não é json nenhum", Dummy)
