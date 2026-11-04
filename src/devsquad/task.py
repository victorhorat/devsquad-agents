from collections.abc import Callable
from pathlib import Path

from devsquad.config import Settings
from devsquad.graph import GraphState, build_graph, initial_state
from devsquad.llm.base import LLMClient
from devsquad.models import TaskResult


def run_task(
    llm: LLMClient,
    settings: Settings,
    task: str,
    context_files: dict[str, str] | None = None,
    max_iterations: int | None = None,
    workspace: Path | None = None,
    module_path: str | None = None,
    write_on_fail: bool = False,
    on_step: Callable[[GraphState], None] | None = None,
) -> TaskResult:
    graph = build_graph(llm, settings)
    state = initial_state(
        task=task,
        context_files=context_files,
        max_iterations=max_iterations or settings.max_iterations,
        test_timeout_seconds=settings.test_timeout_seconds,
    )

    final_state = state
    for snapshot in graph.stream(state, stream_mode="values"):
        final_state = snapshot
        if on_step:
            on_step(final_state)

    written_to = None
    should_write = final_state["status"] == "approved" or write_on_fail
    if should_write and workspace and module_path:
        written_to = _write_to_workspace(
            workspace, module_path, final_state["submission"].code, final_state["submission"].tests
        )

    return TaskResult(
        status=final_state["status"],
        code=final_state["submission"].code,
        tests=final_state["submission"].tests,
        iterations=final_state["iteration"],
        history=final_state["history"],
        total_tokens=final_state["total_tokens"],
        written_to=written_to,
    )


def _write_to_workspace(workspace: Path, module_path: str, code: str, tests: str) -> str:
    module_file = workspace / module_path
    module_file.parent.mkdir(parents=True, exist_ok=True)
    module_file.write_text(code, encoding="utf-8")

    test_file = module_file.parent / f"test_{module_file.stem}.py"
    test_file.write_text(tests, encoding="utf-8")

    return str(module_file)
