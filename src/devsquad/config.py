from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"

    refiner_model: str = ""
    coder_model: str = ""
    qa_model: str = ""

    max_iterations: int = 3
    test_timeout_seconds: int = 30

    def model_for(self, agent: str) -> str:
        override = getattr(self, f"{agent}_model", "")
        return override or self.llm_model


def load_settings() -> Settings:
    return Settings()
