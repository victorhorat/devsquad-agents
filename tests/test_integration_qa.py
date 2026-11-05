import json

from devsquad.agents.integration_qa import judge_integration_result, write_integration_test
from devsquad.llm.fake import FakeLLM
from devsquad.models import ExecutionResult, ModuleOutcome, TaskResult


def _outcome(module_path: str, code: str) -> ModuleOutcome:
    return ModuleOutcome(
        module_path=module_path,
        result=TaskResult(
            status="approved", code=code, tests="", iterations=1, history=[], total_tokens=0
        ),
    )


def test_write_integration_test_parses_response():
    draft_json = json.dumps(
        {"integration_test": "from a import double\n\n\ndef test_x():\n    assert double(2) == 4\n"}
    )
    llm = FakeLLM([draft_json])
    modules = [_outcome("a.py", "def double(x):\n    return x * 2\n")]

    test_code, prompt_tokens, completion_tokens = write_integration_test(llm, "model-x", modules)

    assert "double(2) == 4" in test_code
    assert prompt_tokens > 0


def test_judge_integration_result_approved():
    llm = FakeLLM([json.dumps({"approved": True})])
    modules = [_outcome("a.py", "...")]
    execution = ExecutionResult(passed=True, exit_code=0, stdout="1 passed", stderr="")

    verdict, _, _ = judge_integration_result(llm, "model-x", modules, execution)

    assert verdict.approved is True


def test_judge_integration_result_short_circuits_on_timeout():
    llm = FakeLLM([])
    modules = [_outcome("a.py", "...")]
    execution = ExecutionResult(passed=False, exit_code=-1, stdout="", stderr="", timed_out=True)

    verdict, prompt_tokens, completion_tokens = judge_integration_result(
        llm, "model-x", modules, execution
    )

    assert verdict.approved is False
    assert llm.calls == []
    assert prompt_tokens == 0
    assert completion_tokens == 0
