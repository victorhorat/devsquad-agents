from typing import TypedDict

from langgraph.graph import END, StateGraph

from devsquad.agents.coder import run_coder
from devsquad.agents.qa import run_qa
from devsquad.agents.refiner import run_refiner
from devsquad.config import Settings
from devsquad.llm.base import LLMClient
from devsquad.models import AgentLogEntry, CodeSubmission, ExecutionResult, Spec, Verdict
from devsquad.runner import run_tests


class GraphState(TypedDict):
    task: str
    context_files: dict[str, str]
    max_iterations: int
    test_timeout_seconds: int
    spec: Spec | None
    submission: CodeSubmission | None
    verdict: Verdict | None
    execution: ExecutionResult | None
    iteration: int
    history: list[AgentLogEntry]
    total_tokens: int
    status: str | None


def initial_state(
    task: str,
    context_files: dict[str, str] | None,
    max_iterations: int,
    test_timeout_seconds: int,
) -> GraphState:
    return GraphState(
        task=task,
        context_files=context_files or {},
        max_iterations=max_iterations,
        test_timeout_seconds=test_timeout_seconds,
        spec=None,
        submission=None,
        verdict=None,
        execution=None,
        iteration=0,
        history=[],
        total_tokens=0,
        status=None,
    )


def build_graph(llm: LLMClient, settings: Settings):
    def refiner_node(state: GraphState) -> GraphState:
        spec, prompt_tokens, completion_tokens = run_refiner(
            llm, settings.model_for("refiner"), state["task"], state["context_files"]
        )
        entry = AgentLogEntry(
            agent="refiner",
            iteration=0,
            summary=spec.objective,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return {
            **state,
            "spec": spec,
            "history": [*state["history"], entry],
            "total_tokens": state["total_tokens"] + prompt_tokens + completion_tokens,
        }

    def coder_node(state: GraphState) -> GraphState:
        iteration = state["iteration"] + 1
        submission, prompt_tokens, completion_tokens = run_coder(
            llm,
            settings.model_for("coder"),
            state["spec"],
            previous_attempt=state["submission"],
            previous_verdict=state["verdict"],
            context_files=state["context_files"],
        )
        summary = submission.notes or "código e testes gerados"
        entry = AgentLogEntry(
            agent="coder",
            iteration=iteration,
            summary=summary,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return {
            **state,
            "submission": submission,
            "iteration": iteration,
            "history": [*state["history"], entry],
            "total_tokens": state["total_tokens"] + prompt_tokens + completion_tokens,
        }

    def test_node(state: GraphState) -> GraphState:
        execution = run_tests(
            state["submission"].code,
            state["submission"].tests,
            timeout_seconds=state["test_timeout_seconds"],
        )
        return {**state, "execution": execution}

    def qa_node(state: GraphState) -> GraphState:
        verdict, prompt_tokens, completion_tokens = run_qa(
            llm, settings.model_for("qa"), state["execution"]
        )
        summary = "aprovado" if verdict.approved else (verdict.feedback_for_coder or "reprovado")
        entry = AgentLogEntry(
            agent="qa",
            iteration=state["iteration"],
            summary=summary,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        status = None
        if verdict.approved:
            status = "approved"
        elif state["iteration"] >= state["max_iterations"]:
            status = "max_iterations_reached"
        return {
            **state,
            "verdict": verdict,
            "history": [*state["history"], entry],
            "total_tokens": state["total_tokens"] + prompt_tokens + completion_tokens,
            "status": status,
        }

    def route_after_qa(state: GraphState) -> str:
        return "end" if state["status"] is not None else "retry"

    graph = StateGraph(GraphState)
    graph.add_node("refiner", refiner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("test", test_node)
    graph.add_node("qa", qa_node)

    graph.set_entry_point("refiner")
    graph.add_edge("refiner", "coder")
    graph.add_edge("coder", "test")
    graph.add_edge("test", "qa")
    graph.add_conditional_edges("qa", route_after_qa, {"retry": "coder", "end": END})

    return graph.compile()
