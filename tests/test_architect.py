import json

from devsquad.agents.architect import run_architect
from devsquad.llm.fake import FakeLLM
from devsquad.models import Plan


def test_run_architect_parses_plan():
    plan_json = json.dumps(
        {
            "feature": "modulo de composicao numerica",
            "modules": [
                {"module_path": "a.py", "task": "funcao double", "depends_on": []},
                {"module_path": "b.py", "task": "funcao increment", "depends_on": []},
            ],
        }
    )
    llm = FakeLLM([plan_json])
    plan, prompt_tokens, completion_tokens = run_architect(llm, "model-x", "composicao numerica")

    assert isinstance(plan, Plan)
    assert len(plan.modules) == 2
    assert plan.modules[0].module_path == "a.py"
    assert prompt_tokens > 0
    assert completion_tokens > 0
