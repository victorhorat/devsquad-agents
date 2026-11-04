import statistics
from dataclasses import dataclass
from datetime import date

from devsquad.config import Settings
from devsquad.llm.base import LLMClient
from devsquad.models import TaskResult
from devsquad.task import run_task


@dataclass
class EvalTask:
    name: str
    description: str


TASKS: list[EvalTask] = [
    EvalTask(
        "validar_cpf",
        "funcao validar_cpf(cpf: str) -> bool que valida um CPF brasileiro "
        "verificando os digitos verificadores, aceitando string com ou sem pontuacao",
    ),
    EvalTask(
        "parse_preco_brl",
        "funcao parse_preco_brl(valor: str) -> float que converte uma string de preco "
        "no formato brasileiro, ex: 'R$ 1.234,56', para float (1234.56)",
    ),
    EvalTask(
        "taxa_entrega",
        "funcao calcular_taxa_entrega(distancia_km: float) -> float que calcula a taxa "
        "de entrega: taxa fixa de R$ 5.00 mais R$ 1.20 por km percorrido",
    ),
    EvalTask(
        "agrupar_pedidos_por_restaurante",
        "funcao agrupar_por_restaurante(pedidos: list[dict]) -> dict que recebe uma lista "
        "de pedidos, cada um com a chave 'restaurante_id', e retorna um dict mapeando "
        "restaurante_id para a lista de pedidos daquele restaurante",
    ),
    EvalTask(
        "paginar_lista",
        "funcao paginar(items: list, pagina: int, tamanho_pagina: int) -> list que retorna "
        "a pagina correta (1-indexada) de uma lista; paginas fora do intervalo retornam vazio",
    ),
    EvalTask(
        "validar_email",
        "funcao validar_email(email: str) -> bool que valida se uma string tem o formato "
        "basico de um email valido (algo@dominio.tld)",
    ),
]


@dataclass
class EvalOutcome:
    task_name: str
    result: TaskResult


def run_all(llm: LLMClient, settings: Settings) -> list[EvalOutcome]:
    return [EvalOutcome(task.name, run_task(llm, settings, task.description)) for task in TASKS]


def summarize(outcomes: list[EvalOutcome], model: str) -> str:
    approved = [o for o in outcomes if o.result.status == "approved"]
    success_rate = len(approved) / len(outcomes) if outcomes else 0.0
    avg_iterations = statistics.mean(o.result.iterations for o in outcomes) if outcomes else 0.0
    avg_tokens = statistics.mean(o.result.total_tokens for o in outcomes) if outcomes else 0.0
    avg_latency = statistics.mean(o.result.latency_seconds for o in outcomes) if outcomes else 0.0

    lines = [
        f"## Resultados das evals ({date.today().isoformat()}, modelo: `{model}`)",
        "",
        f"Taxa de sucesso: **{success_rate:.0%}** ({len(approved)}/{len(outcomes)})",
        f"Média de iterações até passar: **{avg_iterations:.1f}**",
        f"Média de tokens por tarefa: **{avg_tokens:.0f}**",
        f"Média de latência por tarefa: **{avg_latency:.1f}s**",
        "",
        "| Tarefa | Status | Iterações | Tokens | Latência (s) |",
        "|---|---|---|---|---|",
    ]
    for outcome in outcomes:
        status_icon = "✅" if outcome.result.status == "approved" else "❌"
        lines.append(
            f"| {outcome.task_name} | {status_icon} | {outcome.result.iterations} | "
            f"{outcome.result.total_tokens} | {outcome.result.latency_seconds} |"
        )
    return "\n".join(lines) + "\n"
