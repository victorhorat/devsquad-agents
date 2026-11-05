from pathlib import Path

import typer
from rich.console import Console

from devsquad.config import load_settings
from devsquad.evals import run_all, summarize
from devsquad.feature import run_feature
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
    "architect": "🏛️ Architect",
    "integration_qa": "🔗 Integration QA",
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


def _full_output_for(agent: str, state: GraphState) -> str | None:
    if agent == "refiner" and state.get("spec"):
        return state["spec"].model_dump_json(indent=2)
    if agent == "coder" and state.get("submission"):
        submission = state["submission"]
        return f"--- código ---\n{submission.code}\n--- testes ---\n{submission.tests}"
    if agent == "qa" and state.get("verdict"):
        return state["verdict"].model_dump_json(indent=2)
    return None


def _make_progress_callback(verbose: bool = False):
    seen = 0

    def on_step(state: GraphState) -> None:
        nonlocal seen
        history = state["history"]
        for entry in history[seen:]:
            label = _AGENT_LABELS.get(entry.agent, entry.agent)
            console.print(f"[bold]{label}[/bold] (iter {entry.iteration}): {entry.summary}")
            if verbose:
                detail = _full_output_for(entry.agent, state)
                if detail:
                    console.print(detail, style="dim", markup=False)
                    console.print()
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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Mostra o output completo de cada agente (spec, código+testes, veredito)",
    ),
) -> None:
    """Roda o time de agentes sobre uma tarefa e, se aprovado, grava no workspace."""
    settings = load_settings()
    llm = OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_output_tokens=settings.llm_max_output_tokens,
    )

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
        on_step=_make_progress_callback(verbose),
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
def build_feature(
    feature: str = typer.Argument(
        ..., help="Descrição da feature (multi-módulo) em linguagem natural"
    ),
    workspace: Path | None = typer.Option(
        None, "--workspace", help="Diretório do projeto onde gravar os módulos gerados"
    ),
    max_module_iterations: int = typer.Option(3, "--max-module-iterations"),
    max_integration_iterations: int = typer.Option(2, "--max-integration-iterations"),
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
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Mostra o plano completo do Architect e o código+testes final de cada módulo",
    ),
) -> None:
    """Planeja uma feature em vários módulos (Architect) e os gera em sequência,
    encadeando contexto entre eles, com um teste de integração no final."""
    settings = load_settings()
    llm = OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_output_tokens=settings.llm_max_output_tokens,
    )

    console.print(f"[bold cyan]Feature:[/bold cyan] {feature}\n")

    context_files = {
        **({} if no_readme_context else _load_readme_context(workspace)),
        **_load_context_dirs(context_dir),
        **_load_context_files(context),
    }

    result = run_feature(
        llm=llm,
        settings=settings,
        feature=feature,
        context_files=context_files,
        max_module_iterations=max_module_iterations,
        max_integration_iterations=max_integration_iterations,
        workspace=workspace,
    )

    console.print(f"[bold]Plano:[/bold] {len(result.plan.modules)} módulo(s)")
    if verbose:
        console.print(result.plan.model_dump_json(indent=2), style="dim", markup=False)
        console.print()
    for entry in result.history:
        label = _AGENT_LABELS.get(entry.agent, entry.agent)
        console.print(f"[bold]{label}[/bold] (iter {entry.iteration}): {entry.summary}")

    if verbose:
        console.print()
        for outcome in result.modules:
            console.print(f"[bold]--- {outcome.module_path} ---[/bold]")
            console.print(
                f"--- código ---\n{outcome.result.code}\n--- testes ---\n{outcome.result.tests}",
                style="dim",
                markup=False,
            )
            console.print()

    console.print()
    if result.status == "approved":
        console.print("[bold green]✅ Feature aprovada (módulos + integração)[/bold green]")
    elif result.status == "partial":
        console.print(
            "[bold yellow]⚠️ Módulos gerados, mas integração não fechou "
            "(veja o histórico acima)[/bold yellow]"
        )
    else:
        console.print("[bold red]❌ Falha ao planejar a feature[/bold red]")

    console.print(f"Tentativas de integração: {result.integration_attempts}")
    console.print(f"Tokens totais: {result.total_tokens}")
    console.print(f"Latência: {result.latency_seconds}s")
    if result.written_to:
        for path in result.written_to:
            console.print(f"Gravado em: {path}")


@app.command()
def eval() -> None:
    """Roda o benchmark de tarefas em evals/ e grava a tabela em evals/results.md."""
    settings = load_settings()
    llm = OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_output_tokens=settings.llm_max_output_tokens,
    )

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
