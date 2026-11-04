from devsquad.llm.base import LLMClient
from devsquad.models import Spec
from devsquad.parsing import parse_structured
from devsquad.prompts import load_prompt

SYSTEM_PROMPT = load_prompt("refiner")


def run_refiner(
    llm: LLMClient,
    model: str,
    task: str,
    context_files: dict[str, str] | None = None,
) -> tuple[Spec, int, int]:
    user_parts = [f"Tarefa:\n{task}"]
    if context_files:
        for path, content in context_files.items():
            user_parts.append(f"\nArquivo de contexto `{path}`:\n```\n{content}\n```")
    user_message = "\n".join(user_parts)

    response = llm.complete(system=SYSTEM_PROMPT, user=user_message, model=model)
    spec = parse_structured(response.content, Spec)
    return spec, response.prompt_tokens, response.completion_tokens
