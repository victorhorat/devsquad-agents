import json

from fastapi.testclient import TestClient

from devsquad.api import app, get_llm, get_settings
from devsquad.config import Settings
from devsquad.llm.fake import FakeLLM

SPEC_JSON = json.dumps(
    {
        "objective": "somar dois inteiros",
        "interface": "def add(a: int, b: int) -> int",
        "acceptance_criteria": ["retorna a soma correta"],
        "test_cases": ["add(2, 3) == 5"],
        "constraints": [],
    }
)
CODE_JSON = json.dumps(
    {
        "code": "def add(a: int, b: int) -> int:\n    return a + b\n",
        "tests": "from solution import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
)
APPROVED_JSON = json.dumps({"approved": True})


def _client_with_fake_llm(script: list[str]) -> TestClient:
    app.dependency_overrides[get_llm] = lambda: FakeLLM(script)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, max_iterations=3)
    return TestClient(app)


def test_health_returns_ok():
    client = _client_with_fake_llm([])
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_task_returns_approved_result():
    client = _client_with_fake_llm([SPEC_JSON, CODE_JSON, APPROVED_JSON])
    response = client.post("/tasks", json={"task": "soma dois inteiros", "max_iterations": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["iterations"] == 1
    assert len(body["history"]) == 3
