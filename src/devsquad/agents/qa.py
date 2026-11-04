from devsquad.llm.base import LLMClient
from devsquad.models import ExecutionResult, Verdict
from devsquad.parsing import parse_structured
from devsquad.prompts import load_prompt

SYSTEM_PROMPT = load_prompt("qa")


def run_qa(
    llm: LLMClient,
    model: str,
    execution: ExecutionResult,
) -> tuple[Verdict, int, int]:
    if execution.timed_out:
        return (
            Verdict(
                approved=False,
                failing_test=None,
                traceback_summary="Execução excedeu o timeout configurado.",
                likely_cause="Possível loop infinito ou operação bloqueante no código gerado.",
                feedback_for_coder="Revise o código em busca de loops sem condição de parada "
                "ou chamadas bloqueantes; o teste precisa terminar dentro do timeout.",
            ),
            0,
            0,
        )

    user_message = (
        f"exit_code: {execution.exit_code}\n"
        f"passed: {execution.passed}\n\n"
        f"stdout:\n{execution.stdout}\n\n"
        f"stderr:\n{execution.stderr}"
    )

    response = llm.complete(system=SYSTEM_PROMPT, user=user_message, model=model)
    verdict = parse_structured(response.content, Verdict)
    return verdict, response.prompt_tokens, response.completion_tokens
