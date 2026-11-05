from devsquad.llm.base import LLMClient
from devsquad.models import Plan
from devsquad.parsing import parse_structured
from devsquad.prompts import load_prompt

SYSTEM_PROMPT = load_prompt("architect")


def run_architect(
    llm: LLMClient,
    model: str,
    feature: str,
    context_files: dict[str, str] | None = None,
) -> tuple[Plan, int, int]:
    user_parts = [f"Feature:\n{feature}"]
    if context_files:
        for path, content in context_files.items():
            user_parts.append(f"\nArquivo de contexto `{path}`:\n```\n{content}\n```")
    user_message = "\n".join(user_parts)

    response = llm.complete(system=SYSTEM_PROMPT, user=user_message, model=model)
    plan = parse_structured(response.content, Plan)
    return plan, response.prompt_tokens, response.completion_tokens
