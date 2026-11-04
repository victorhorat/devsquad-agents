from importlib import resources


def load_prompt(name: str) -> str:
    """Carrega um prompt de sistema de devsquad/prompts/<name>.md."""
    return resources.files(__package__).joinpath(f"{name}.md").read_text(encoding="utf-8")
