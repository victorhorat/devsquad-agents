from devsquad.llm.base import LLMClient
from devsquad.models import CodeSubmission, Spec, Verdict
from devsquad.parsing import parse_structured
from devsquad.prompts import load_prompt

SYSTEM_PROMPT = load_prompt("coder")


def run_coder(
    llm: LLMClient,
    model: str,
    spec: Spec,
    previous_attempt: CodeSubmission | None = None,
    previous_verdict: Verdict | None = None,
    context_files: dict[str, str] | None = None,
) -> tuple[CodeSubmission, int, int]:
    user_parts = [f"Especificação:\n{spec.model_dump_json(indent=2)}"]

    if context_files:
        for path, content in context_files.items():
            user_parts.append(f"\nArquivo de contexto `{path}`:\n```\n{content}\n```")

    if previous_attempt and previous_verdict and not previous_verdict.approved:
        user_parts.append(
            "\nTentativa anterior (código):\n```python\n" + previous_attempt.code + "\n```"
        )
        user_parts.append(
            "\nTentativa anterior (testes):\n```python\n" + previous_attempt.tests + "\n```"
        )
        user_parts.append(
            "\nFeedback do QA sobre a tentativa anterior:\n"
            f"- teste que falhou: {previous_verdict.failing_test}\n"
            f"- resumo do traceback: {previous_verdict.traceback_summary}\n"
            f"- causa provável: {previous_verdict.likely_cause}\n"
            f"- o que corrigir: {previous_verdict.feedback_for_coder}"
        )

    user_message = "\n".join(user_parts)

    response = llm.complete(system=SYSTEM_PROMPT, user=user_message, model=model)
    submission = parse_structured(response.content, CodeSubmission)
    return submission, response.prompt_tokens, response.completion_tokens
