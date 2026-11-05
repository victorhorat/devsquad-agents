from pydantic import BaseModel

from devsquad.llm.base import LLMClient
from devsquad.models import ExecutionResult, IntegrationVerdict, ModuleOutcome
from devsquad.parsing import parse_structured
from devsquad.prompts import load_prompt

_WRITER_SYSTEM_PROMPT = load_prompt("integration_test_writer")
_QA_SYSTEM_PROMPT = load_prompt("integration_qa")


class _IntegrationTestDraft(BaseModel):
    integration_test: str


def write_integration_test(
    llm: LLMClient,
    model: str,
    modules: list[ModuleOutcome],
) -> tuple[str, int, int]:
    parts = ["Módulos aprovados disponíveis para o teste de integração:"]
    for outcome in modules:
        parts.append(f"\nArquivo `{outcome.module_path}`:\n```python\n{outcome.result.code}\n```")
    user_message = "\n".join(parts)

    response = llm.complete(system=_WRITER_SYSTEM_PROMPT, user=user_message, model=model)
    draft = parse_structured(response.content, _IntegrationTestDraft)
    return draft.integration_test, response.prompt_tokens, response.completion_tokens


def judge_integration_result(
    llm: LLMClient,
    model: str,
    modules: list[ModuleOutcome],
    execution: ExecutionResult,
) -> tuple[IntegrationVerdict, int, int]:
    if execution.timed_out:
        return (
            IntegrationVerdict(
                approved=False,
                failing_module=None,
                traceback_summary="Execução excedeu o timeout configurado.",
                feedback_for_coder="Revise os módulos em busca de loops sem condição de "
                "parada ou chamadas bloqueantes entre eles.",
            ),
            0,
            0,
        )

    module_list = ", ".join(outcome.module_path for outcome in modules)
    user_message = (
        f"Módulos envolvidos: {module_list}\n\n"
        f"exit_code: {execution.exit_code}\n"
        f"passed: {execution.passed}\n\n"
        f"stdout:\n{execution.stdout}\n\n"
        f"stderr:\n{execution.stderr}"
    )

    response = llm.complete(system=_QA_SYSTEM_PROMPT, user=user_message, model=model)
    verdict = parse_structured(response.content, IntegrationVerdict)
    return verdict, response.prompt_tokens, response.completion_tokens
