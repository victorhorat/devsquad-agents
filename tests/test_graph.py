import json

from devsquad.config import Settings
from devsquad.graph import build_graph, initial_state
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

WORKING_CODE_JSON = json.dumps(
    {
        "code": "def add(a: int, b: int) -> int:\n    return a + b\n",
        "tests": "from solution import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
)

BUGGY_CODE_JSON = json.dumps(
    {
        "code": "def add(a: int, b: int) -> int:\n    return a - b\n",
        "tests": "from solution import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
    }
)

APPROVED_JSON = json.dumps({"approved": True})
REJECTED_JSON = json.dumps(
    {
        "approved": False,
        "failing_test": "test_add",
        "traceback_summary": "assert -1 == 5",
        "likely_cause": "operador errado",
        "feedback_for_coder": "use + em vez de -",
    }
)


def _settings(max_iterations: int) -> Settings:
    return Settings(_env_file=None, max_iterations=max_iterations)


def test_graph_approves_on_first_try():
    llm = FakeLLM([SPEC_JSON, WORKING_CODE_JSON, APPROVED_JSON])
    graph = build_graph(llm, _settings(max_iterations=3))
    state = initial_state("soma dois inteiros", None, max_iterations=3, test_timeout_seconds=30)

    final_state = graph.invoke(state)

    assert final_state["status"] == "approved"
    assert final_state["iteration"] == 1
    assert len(final_state["history"]) == 3  # refiner, coder, qa


def test_graph_retries_after_qa_rejects_then_approves():
    llm = FakeLLM([SPEC_JSON, BUGGY_CODE_JSON, REJECTED_JSON, WORKING_CODE_JSON, APPROVED_JSON])
    graph = build_graph(llm, _settings(max_iterations=3))
    state = initial_state("soma dois inteiros", None, max_iterations=3, test_timeout_seconds=30)

    final_state = graph.invoke(state)

    assert final_state["status"] == "approved"
    assert final_state["iteration"] == 2
    assert len(final_state["history"]) == 5  # refiner, coder, qa, coder, qa


def test_graph_stops_at_max_iterations_without_approval():
    llm = FakeLLM([SPEC_JSON, BUGGY_CODE_JSON, REJECTED_JSON])
    graph = build_graph(llm, _settings(max_iterations=1))
    state = initial_state("soma dois inteiros", None, max_iterations=1, test_timeout_seconds=30)

    final_state = graph.invoke(state)

    assert final_state["status"] == "max_iterations_reached"
    assert final_state["iteration"] == 1
