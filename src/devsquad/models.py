from typing import Literal

from pydantic import BaseModel, Field


class Spec(BaseModel):
    """Especificação estruturada produzida pelo Refiner."""

    objective: str
    interface: str = Field(description="Assinatura(s) de função/classe esperadas")
    acceptance_criteria: list[str]
    test_cases: list[str] = Field(description="Casos de teste a cobrir, incluindo bordas")
    constraints: list[str] = Field(default_factory=list)


class CodeSubmission(BaseModel):
    """Código e testes produzidos pelo Coder em uma iteração."""

    code: str
    tests: str
    notes: str = ""


class TestExecutionResult(BaseModel):
    """Resultado bruto de rodar o pytest gerado."""

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class Verdict(BaseModel):
    """Veredito estruturado produzido pelo QA."""

    approved: bool
    failing_test: str | None = None
    traceback_summary: str | None = None
    likely_cause: str | None = None
    feedback_for_coder: str | None = None


class AgentLogEntry(BaseModel):
    agent: Literal["refiner", "coder", "qa"]
    iteration: int
    summary: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class TaskResult(BaseModel):
    status: Literal["approved", "max_iterations_reached"]
    code: str
    tests: str
    iterations: int
    history: list[AgentLogEntry]
    total_tokens: int
    written_to: str | None = None
