import json

from devsquad.config import Settings
from devsquad.feature import run_feature
from devsquad.llm.fake import FakeLLM

PLAN_JSON = json.dumps(
    {
        "feature": "modulo de composicao numerica",
        "modules": [
            {"module_path": "a.py", "task": "funcao que dobra um numero", "depends_on": []},
            {"module_path": "b.py", "task": "funcao que incrementa um numero", "depends_on": []},
        ],
    }
)

SPEC_A_JSON = json.dumps(
    {
        "objective": "dobrar um numero",
        "interface": "def double(x: int) -> int",
        "acceptance_criteria": ["retorna o dobro"],
        "test_cases": ["double(3) == 6"],
        "constraints": [],
    }
)
CODE_A_OK_JSON = json.dumps(
    {
        "code": "def double(x: int) -> int:\n    return x * 2\n",
        "tests": "from solution import double\n\n\ndef test_double():\n    assert double(3) == 6\n",
    }
)

SPEC_B_JSON = json.dumps(
    {
        "objective": "incrementar um numero",
        "interface": "def increment(x: int) -> int",
        "acceptance_criteria": ["retorna x mais 1"],
        "test_cases": ["increment(1) == 2"],
        "constraints": [],
    }
)
_INCREMENT_TEST = (
    "from solution import increment\n\n\ndef test_increment():\n    assert increment(1) == 2\n"
)
CODE_B_BUGGY_JSON = json.dumps(
    {"code": "def increment(x: int) -> int:\n    return x - 1\n", "tests": _INCREMENT_TEST}
)
CODE_B_FIXED_JSON = json.dumps(
    {"code": "def increment(x: int) -> int:\n    return x + 1\n", "tests": _INCREMENT_TEST}
)

APPROVED_JSON = json.dumps({"approved": True})

INTEGRATION_TEST_JSON = json.dumps(
    {
        "integration_test": (
            "from a import double\nfrom b import increment\n\n\n"
            "def test_compose():\n    assert increment(double(3)) == 7\n"
        )
    }
)
INTEGRATION_REJECTED_JSON = json.dumps(
    {
        "approved": False,
        "failing_module": "b.py",
        "traceback_summary": "assert 5 == 7",
        "feedback_for_coder": "increment deve somar 1, nao subtrair",
    }
)


def _settings() -> Settings:
    return Settings(_env_file=None, max_integration_iterations=2)


def test_feature_approves_when_everything_passes_first_try():
    llm = FakeLLM(
        [
            PLAN_JSON,
            SPEC_A_JSON,
            CODE_A_OK_JSON,
            APPROVED_JSON,
            SPEC_B_JSON,
            CODE_B_FIXED_JSON,
            APPROVED_JSON,
            INTEGRATION_TEST_JSON,
            APPROVED_JSON,
        ]
    )

    result = run_feature(llm, _settings(), "composicao numerica")

    assert result.status == "approved"
    assert result.integration_attempts == 1
    assert len(result.modules) == 2


def test_feature_fixes_module_after_integration_failure():
    llm = FakeLLM(
        [
            PLAN_JSON,
            SPEC_A_JSON,
            CODE_A_OK_JSON,
            APPROVED_JSON,
            SPEC_B_JSON,
            CODE_B_BUGGY_JSON,
            APPROVED_JSON,  # per-module QA rubber-stamps despite the real bug
            INTEGRATION_TEST_JSON,
            INTEGRATION_REJECTED_JSON,
            CODE_B_FIXED_JSON,  # Coder fix targeted at b.py
            INTEGRATION_TEST_JSON,
            APPROVED_JSON,
        ]
    )

    result = run_feature(llm, _settings(), "composicao numerica")

    assert result.status == "approved"
    assert result.integration_attempts == 2
    fixed_module = next(m for m in result.modules if m.module_path == "b.py")
    assert "x + 1" in fixed_module.result.code


def test_feature_reports_partial_when_integration_budget_runs_out():
    settings = Settings(_env_file=None, max_integration_iterations=1)
    llm = FakeLLM(
        [
            PLAN_JSON,
            SPEC_A_JSON,
            CODE_A_OK_JSON,
            APPROVED_JSON,
            SPEC_B_JSON,
            CODE_B_BUGGY_JSON,
            APPROVED_JSON,
            INTEGRATION_TEST_JSON,
            INTEGRATION_REJECTED_JSON,
        ]
    )

    result = run_feature(llm, settings, "composicao numerica")

    assert result.status == "partial"
    assert result.integration_attempts == 1
