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


class ExecutionResult(BaseModel):
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
    agent: Literal["refiner", "coder", "qa", "architect", "integration_qa"]
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
    latency_seconds: float = 0.0
    written_to: str | None = None


class PlannedModule(BaseModel):
    """Um módulo do plano produzido pelo Architect."""

    module_path: str
    task: str
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Plano produzido pelo Architect pra uma feature multi-módulo."""

    feature: str
    modules: list[PlannedModule]


class ModuleOutcome(BaseModel):
    """Resultado de gerar um módulo do plano."""

    module_path: str
    result: TaskResult


class IntegrationVerdict(BaseModel):
    """Veredito estruturado produzido pelo Integration QA."""

    approved: bool
    failing_module: str | None = None
    traceback_summary: str | None = None
    feedback_for_coder: str | None = None


class FeatureResult(BaseModel):
    status: Literal["approved", "partial", "plan_failed"]
    plan: Plan
    modules: list[ModuleOutcome]
    history: list[AgentLogEntry]
    integration_attempts: int
    total_tokens: int
    latency_seconds: float = 0.0
    written_to: list[str] = Field(default_factory=list)
