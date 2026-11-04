from devsquad.evals import EvalOutcome, summarize
from devsquad.models import TaskResult


def _result(
    status: str, iterations: int = 1, tokens: int = 100, latency: float = 1.0
) -> TaskResult:
    return TaskResult(
        status=status,
        code="code",
        tests="tests",
        iterations=iterations,
        history=[],
        total_tokens=tokens,
        latency_seconds=latency,
    )


def test_summarize_reports_success_rate_and_averages():
    outcomes = [
        EvalOutcome("task_a", _result("approved", iterations=1, tokens=100, latency=1.0)),
        EvalOutcome(
            "task_b", _result("max_iterations_reached", iterations=3, tokens=300, latency=3.0)
        ),
    ]
    report = summarize(outcomes, model="test-model")

    assert "50%" in report
    assert "task_a" in report
    assert "task_b" in report
    assert "test-model" in report
