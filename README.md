# devsquad-agents

> **EN summary:** A small multi-agent dev team (Refiner → Coder → QA) built with LangGraph that turns a natural-language task into tested Python code. Runs real pytest in an isolated subprocess, loops Coder↔QA until green, and works against any OpenAI-compatible LLM endpoint (Gemini free tier by default). Ships as a CLI and a FastAPI service, with eval benchmarks tracking success rate, iterations, tokens and latency.

> ⚠️ **Rascunho de arquitetura para revisão — ainda não implementado.** Este README descreve o que vai ser construído. Seções marcadas com `[pendente]` serão preenchidas depois que o código e as evals existirem.

---

## 1. O que é

Um "time de desenvolvimento" de agentes de IA: você descreve uma tarefa em português natural, e três agentes especializados (Refiner, Coder, QA) colaboram em loop até entregar código Python com testes reais passando.

`[pendente: GIF/print do terminal rodando `devsquad run`]`

## 2. Por que existe

Fiz este projeto para o meu portfólio de IA Generativa. Mas ele não é só uma demo: é a ferramenta que eu uso para construir os próximos dois projetos do portfólio, apontando o `--workspace` para as pastas deles.

- `[pendente: link para o agente de pedidos de comida]`
- `[pendente: link para o RAG de avaliações de restaurantes]`

## 3. Arquitetura

### Visão geral

Grafo de estado (LangGraph) com três nós de agente e uma aresta condicional que decide entre repetir o ciclo de correção ou finalizar.

```mermaid
flowchart TD
    Start([Tarefa em linguagem natural]) --> Refiner

    Refiner["🧭 Refiner\n(especificação estruturada)"] --> Coder

    Coder["👩‍💻 Coder\n(gera código + testes pytest)"] --> Runner

    Runner["⚙️ Test Runner\n(subprocess isolado, timeout, sem env sensível)"]
    Runner --> QA

    QA{"🔍 QA\nanalisa resultado dos testes"}
    QA -->|testes passaram| Approve([✅ Aprovado])
    QA -->|falhou e iterações < MAX| Coder
    QA -->|falhou e iterações == MAX| Fail([❌ Limite de iterações])

    Approve --> Write["💾 Grava código + testes\nno --workspace"]
```

### Componentes

| Componente | Responsabilidade |
|---|---|
| **Refiner** | Recebe a tarefa bruta (+ arquivos de contexto opcionais do workspace) e produz uma especificação estruturada: objetivo, assinaturas de interface, critérios de aceite, casos de teste (incluindo bordas) e restrições. Saída validada com Pydantic. |
| **Coder** | Gera o módulo Python e os testes pytest a partir da spec. A partir da 2ª iteração, recebe também o diagnóstico do QA e corrige. |
| **Test Runner** | Executa o pytest gerado em diretório temporário isolado via `subprocess`, com timeout (30s padrão), sem herdar `LLM_API_KEY`/variáveis sensíveis, saída capturada e truncada. Não é um sandbox completo — ver seção 7. |
| **QA** | Interpreta a saída do Test Runner e produz um veredito estruturado (Pydantic): aprovado ou não, teste que falhou, traceback resumido, causa provável. |
| **LLM Client** | Cliente genérico compatível com OpenAI (`base_url` livre), com retry/backoff para 429/5xx, timeout, e parsing tolerante de JSON para respostas estruturadas quando o provedor não suporta `response_format`. Modelo configurável por agente. |
| **Orquestrador (LangGraph)** | Mantém o estado tipado do grafo (spec, código atual, histórico de tentativas, contagem de iterações, tokens) e a aresta condicional QA→Coder / QA→Fim. |

### Loop de autocorreção

```
Coder → Test Runner → QA
          ↑               │
          └── falhou ─────┘   (até MAX_ITERATIONS, padrão 3)
```

### Fluxo de dados (alto nível)

1. CLI/API recebe `task` (+ opcional `context`: arquivos existentes do workspace, `max_iterations`).
2. Refiner → `Spec` (Pydantic).
3. Coder(`Spec`, histórico QA) → `{codigo, testes}`.
4. Test Runner(`{codigo, testes}`) → `ResultadoExecucao` (stdout/stderr truncado, passou/falhou).
5. QA(`ResultadoExecucao`) → `Veredito` (aprovado | corrigir com diagnóstico).
6. Se aprovado ou limite atingido → grava no `--workspace` (ou não, se falhou e sem `--write-on-fail`) e retorna resultado final: código, testes, status, nº de iterações, histórico por agente, tokens.

## 4. Como rodar

`[pendente — depende da Fase 1]`

```bash
# instalação local (uv)
uv sync

# variáveis de ambiente
cp .env.example .env
```

### Configuração de provedor (qualquer endpoint compatível com OpenAI)

```env
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_API_KEY=...
LLM_MODEL=gemini-2.0-flash

# opcional: modelo diferente por agente
REFINER_MODEL=
CODER_MODEL=
QA_MODEL=
```

Exemplos de outros provedores oficiais: `[pendente — Gemini | Groq | OpenRouter | DeepSeek | Ollama local]`

### Docker

`[pendente — depende da Fase 3]`

## 5. CLI e API

### CLI

```bash
devsquad run "função que valida CPF com dígitos verificadores" \
  --workspace ../food-order-agent \
  --module src/validators/cpf.py \
  --max-iterations 3
```

### API

- `POST /tasks` — `{ "task": "...", "max_iterations": 3 }` → resultado completo
- `GET /health`
- Swagger em `/docs`

`[pendente: exemplos de request/response reais]`

## 6. Resultados das evals

`[pendente — depende da Fase 4: tabela com taxa de sucesso, média de iterações, tokens, latência, modelo usado e data]`

## 7. Decisões técnicas e trade-offs

- **Por que LangGraph:** estado tipado explícito e aresta condicional modelam naturalmente o loop Coder↔QA, sem precisar de uma máquina de estados escrita à mão.
- **Por que cliente compatível com OpenAI em vez de SDK nativo de cada provedor:** permite trocar de provedor só mudando `LLM_BASE_URL`/`LLM_MODEL`, sem reescrever código — inclusive para endpoints locais.
- **Por que executar os testes de verdade (e não só pedir pro QA "revisar" o código):** um LLM julgando código visualmente erra; rodar pytest de fato dá um veredito objetivo e verificável.
- **Limites do sandbox atual:** subprocess isolado com timeout e sem variáveis sensíveis reduz risco, mas não é isolamento completo de SO/filesystem/rede. Próximo passo natural é rodar em container descartável (`SANDBOX=docker`, se der tempo).

## 8. Próximos passos

- Sandbox real em container descartável.
- Mais agentes: `Architect` (decisões de design antes do Coder), `Docs` (gera docstrings/README do módulo).
- Cache de respostas do LLM entre iterações.
- UI simples para acompanhar o grafo em execução.
