from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from devsquad.config import Settings, load_settings
from devsquad.llm.base import LLMClient
from devsquad.llm.openai_client import OpenAICompatibleClient
from devsquad.models import TaskResult
from devsquad.task import run_task

_state: dict[str, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    _state["settings"] = settings
    _state["llm"] = OpenAICompatibleClient(
        base_url=settings.llm_base_url, api_key=settings.llm_api_key
    )
    yield
    _state.clear()


app = FastAPI(
    title="devsquad-agents",
    description="Time de agentes de IA (Refiner, Coder, QA) que gera código testado",
    version="0.1.0",
    lifespan=lifespan,
)


def get_settings() -> Settings:
    return _state["settings"]  # type: ignore[return-value]


def get_llm() -> LLMClient:
    return _state["llm"]  # type: ignore[return-value]


class TaskRequest(BaseModel):
    task: str
    max_iterations: int = 3


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskResult)
def create_task(
    request: TaskRequest,
    llm: LLMClient = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> TaskResult:
    return run_task(
        llm=llm,
        settings=settings,
        task=request.task,
        max_iterations=request.max_iterations,
    )
