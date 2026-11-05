import time
from pathlib import Path

from devsquad.agents.architect import run_architect
from devsquad.agents.coder import run_coder
from devsquad.agents.integration_qa import judge_integration_result, write_integration_test
from devsquad.config import Settings
from devsquad.llm.base import LLMClient
from devsquad.models import (
    AgentLogEntry,
    CodeSubmission,
    FeatureResult,
    ModuleOutcome,
    Spec,
    Verdict,
)
from devsquad.runner import run_integration_tests
from devsquad.task import run_task


def run_feature(
    llm: LLMClient,
    settings: Settings,
    feature: str,
    context_files: dict[str, str] | None = None,
    max_module_iterations: int | None = None,
    max_integration_iterations: int | None = None,
    workspace: Path | None = None,
) -> FeatureResult:
    started_at = time.monotonic()
    history: list[AgentLogEntry] = []
    total_tokens = 0
    max_integration = max_integration_iterations or settings.max_integration_iterations

    plan, prompt_tokens, completion_tokens = run_architect(
        llm, settings.model_for("architect"), feature, context_files
    )
    total_tokens += prompt_tokens + completion_tokens
    history.append(
        AgentLogEntry(
            agent="architect",
            iteration=0,
            summary=plan.feature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    )

    modules: list[ModuleOutcome] = []
    accumulated_context = dict(context_files or {})

    for planned in plan.modules:
        module_result = run_task(
            llm=llm,
            settings=settings,
            task=planned.task,
            context_files=accumulated_context,
            max_iterations=max_module_iterations,
        )
        history.extend(module_result.history)
        total_tokens += module_result.total_tokens
        modules.append(ModuleOutcome(module_path=planned.module_path, result=module_result))
        accumulated_context[planned.module_path] = module_result.code

    status = "partial"
    integration_attempts = 0

    for attempt in range(1, max_integration + 1):
        integration_attempts = attempt
        module_files = {m.module_path: m.result.code for m in modules}

        test_code, prompt_tokens, completion_tokens = write_integration_test(
            llm, settings.model_for("integration_qa"), modules
        )
        total_tokens += prompt_tokens + completion_tokens

        execution = run_integration_tests(module_files, test_code, settings.test_timeout_seconds)

        verdict, prompt_tokens, completion_tokens = judge_integration_result(
            llm, settings.model_for("integration_qa"), modules, execution
        )
        total_tokens += prompt_tokens + completion_tokens
        summary = "aprovado" if verdict.approved else (verdict.feedback_for_coder or "reprovado")
        history.append(
            AgentLogEntry(
                agent="integration_qa",
                iteration=attempt,
                summary=summary,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

        if verdict.approved:
            status = "approved"
            break

        if attempt == max_integration:
            break

        target = next((m for m in modules if m.module_path == verdict.failing_module), None)
        if target is None:
            break

        planned_module = next(p for p in plan.modules if p.module_path == target.module_path)
        synthetic_spec = Spec(
            objective=planned_module.task,
            interface="(ver código atual do módulo)",
            acceptance_criteria=[
                "o código deve continuar passando nos testes unitários existentes",
                "o código deve se integrar corretamente com os módulos dependentes",
            ],
            test_cases=[],
        )
        other_modules_context = {
            m.module_path: m.result.code for m in modules if m.module_path != target.module_path
        }
        fixed_submission, prompt_tokens, completion_tokens = run_coder(
            llm,
            settings.model_for("coder"),
            synthetic_spec,
            previous_attempt=CodeSubmission(code=target.result.code, tests=target.result.tests),
            previous_verdict=Verdict(
                approved=False,
                traceback_summary=verdict.traceback_summary,
                feedback_for_coder=verdict.feedback_for_coder,
            ),
            context_files=other_modules_context,
        )
        total_tokens += prompt_tokens + completion_tokens
        history.append(
            AgentLogEntry(
                agent="coder",
                iteration=attempt,
                summary=fixed_submission.notes or "correção de integração",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )
        target.result.code = fixed_submission.code
        target.result.tests = fixed_submission.tests
        accumulated_context[target.module_path] = fixed_submission.code

    written: list[str] = []
    if workspace:
        for outcome in modules:
            module_file = workspace / outcome.module_path
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text(outcome.result.code, encoding="utf-8")
            test_file = module_file.parent / f"test_{module_file.stem}.py"
            test_file.write_text(outcome.result.tests, encoding="utf-8")
            written.append(str(module_file))

    return FeatureResult(
        status=status,
        plan=plan,
        modules=modules,
        history=history,
        integration_attempts=integration_attempts,
        total_tokens=total_tokens,
        latency_seconds=round(time.monotonic() - started_at, 3),
        written_to=written,
    )
