import json

from devsquad.agents.coder import run_coder
from devsquad.agents.qa import run_qa
from devsquad.agents.refiner import run_refiner
from devsquad.llm.fake import FakeLLM
from devsquad.models import ExecutionResult, Spec


def test_run_refiner_parses_spec():
    spec_json = json.dumps(
        {
            "objective": "validar CPF",
            "interface": "def validar_cpf(cpf: str) -> bool",
            "acceptance_criteria": ["retorna True para CPF válido"],
            "test_cases": ["CPF válido", "CPF com letras"],
            "constraints": [],
        }
    )
    llm = FakeLLM([spec_json])
    spec, prompt_tokens, completion_tokens = run_refiner(llm, "model-x", "valide um CPF")
    assert isinstance(spec, Spec)
    assert spec.objective == "validar CPF"
    assert prompt_tokens > 0
    assert completion_tokens > 0


def test_run_coder_includes_previous_feedback_in_prompt():
    code_json = json.dumps({"code": "def f(): return 1", "tests": "def test_f(): assert True"})
    llm = FakeLLM([code_json])
    spec = Spec(
        objective="obj",
        interface="def f()",
        acceptance_criteria=["ok"],
        test_cases=["caso 1"],
    )
    submission, _, _ = run_coder(llm, "model-x", spec)
    assert submission.code == "def f(): return 1"
    assert "Especificação" in llm.calls[0][1]


def test_run_qa_parses_verdict_when_tests_pass():
    verdict_json = json.dumps({"approved": True})
    llm = FakeLLM([verdict_json])
    execution = ExecutionResult(passed=True, exit_code=0, stdout="1 passed", stderr="")
    verdict, _, _ = run_qa(llm, "model-x", execution)
    assert verdict.approved is True


def test_run_qa_short_circuits_on_timeout_without_calling_llm():
    llm = FakeLLM([])
    execution = ExecutionResult(passed=False, exit_code=-1, stdout="", stderr="", timed_out=True)
    verdict, prompt_tokens, completion_tokens = run_qa(llm, "model-x", execution)
    assert verdict.approved is False
    assert llm.calls == []
    assert prompt_tokens == 0
    assert completion_tokens == 0
