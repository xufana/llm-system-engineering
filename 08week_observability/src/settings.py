from typing import Literal

from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIModelConfig(BaseModel):
    name: str
    base_url: HttpUrl
    key: str = ""
    timeout: int = 60
    max_retries: int = 2


class LangfuseConfig(BaseModel):
    base_url: HttpUrl
    public_key: str
    secret_key: str
    environment: Literal["production", "development", "staging"] = "development"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    llm: APIModelConfig
    embedder: APIModelConfig

    langfuse: LangfuseConfig

    qdrant_host: HttpUrl
    qdrant_collection: str
