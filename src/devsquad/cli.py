from pathlib import Path

import typer
from rich.console import Console

from devsquad.config import load_settings
from devsquad.evals import run_all, summarize
from devsquad.graph import GraphState
from devsquad.llm.openai_client import OpenAICompatibleClient
from devsquad.task import run_task

EVALS_RESULTS_PATH = Path(__file__).resolve().parents[2] / "evals" / "results.md"

app = typer.Typer(help="devsquad-agents: time de agentes de IA que gera código testado")
console = Console()

_AGENT_LABELS = {
    "refiner": "🧭 Refiner",
    "coder": "👩‍💻 Coder",
    "qa": "🔍 QA",
}


def _load_context_files(paths: list[str]) -> dict[str, str]:
    context: dict[str, str] = {}
    for raw_path in paths:
        path = Path(raw_path)
        context[raw_path] = path.read_text(encoding="utf-8")
    return context


def _load_context_dirs(dirs: list[str]) -> dict[str, str]:
    context: dict[str, str] = {}
    for raw_dir in dirs:
        for path in sorted(Path(raw_dir).glob("*.py")):
            if path.name.startswith("test_"):
                continue
            context[str(path)] = path.read_text(encoding="utf-8")
    return context


def _load_readme_context(workspace: Path | None) -> dict[str, str]:
    if not workspace:
        return {}
    readme = workspace / "README.md"
    if not readme.is_file():
        return {}
    return {str(readme): readme.read_text(encoding="utf-8")}


def _make_progress_callback():
    seen = 0

    def on_step(state: GraphState) -> None:
        nonlocal seen
        history = state["history"]
        for entry in history[seen:]:
            label = _AGENT_LABELS.get(entry.agent, entry.agent)
            console.print(f"[bold]{label}[/bold] (iter {entry.iteration}): {entry.summary}")
        seen = len(history)

    return on_step


@app.command()
def run(
    task: str = typer.Argument(..., help="Descrição da tarefa em linguagem natural"),
    workspace: Path | None = typer.Option(
        None, "--workspace", help="Diretório do projeto onde gravar o resultado aprovado"
    ),
    module: str | None = typer.Option(
        None, "--module", help="Caminho (relativo ao workspace) do módulo a gerar"
    ),
    max_iterations: int = typer.Option(3, "--max-iterations"),
    context: list[str] = typer.Option(
        [], "--context", help="Arquivo(s) existentes do workspace para dar de contexto"
    ),
    context_dir: list[str] = typer.Option(
        [],
        "--context-dir",
        help="Pasta(s) cujos arquivos .py (exceto test_*.py) entram como contexto",
    ),
    no_readme_context: bool = typer.Option(
        False,
        "--no-readme-context",
        help="Não incluir automaticamente o README.md do --workspace como contexto",
    ),
    write_on_fail: bool = typer.Option(
        False, "--write-on-fail", help="Grava no workspace mesmo se o QA não aprovar"
    ),
) -> None:
    """Roda o time de agentes sobre uma tarefa e, se aprovado, grava no workspace."""
    settings = load_settings()
    llm = OpenAICompatibleClient(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    console.print(f"[bold cyan]Tarefa:[/bold cyan] {task}\n")

    context_files = {
        **({} if no_readme_context else _load_readme_context(workspace)),
        **_load_context_dirs(context_dir),
        **_load_context_files(context),
    }

    result = run_task(
        llm=llm,
        settings=settings,
        task=task,
        context_files=context_files,
        max_iterations=max_iterations,
        workspace=workspace,
        module_path=module,
        write_on_fail=write_on_fail,
        on_step=_make_progress_callback(),
    )

    console.print()
    if result.status == "approved":
        console.print("[bold green]✅ Aprovado[/bold green]")
    else:
        console.print("[bold red]❌ Limite de iterações atingido sem aprovação[/bold red]")

    console.print(f"Iterações: {result.iterations}")
    console.print(f"Tokens totais: {result.total_tokens}")
    console.print(f"Latência: {result.latency_seconds}s")
    if result.written_to:
        console.print(f"Gravado em: {result.written_to}")
    elif workspace and module:
        console.print("Nada foi gravado (use --write-on-fail para gravar mesmo reprovado).")


@app.command()
def eval() -> None:
    """Roda o benchmark de tarefas em evals/ e grava a tabela em evals/results.md."""
    settings = load_settings()
    llm = OpenAICompatibleClient(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

    outcomes = run_all(llm, settings)
    for outcome in outcomes:
        icon = "✅" if outcome.result.status == "approved" else "❌"
        console.print(f"{icon} {outcome.task_name} ({outcome.result.iterations} iter)")

    report = summarize(outcomes, model=settings.llm_model)
    EVALS_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVALS_RESULTS_PATH.write_text(report, encoding="utf-8")

    console.print()
    console.print(report)
    console.print(f"[bold]Resultado gravado em {EVALS_RESULTS_PATH}[/bold]")


if __name__ == "__main__":
    app()
