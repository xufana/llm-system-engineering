from langfuse import Langfuse, get_client
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient

from schemes import RolesEnum
from src.clients.llm import get_llm_client
from src.clients.qdrant import get_qdrant_client
from src.pipeline.base_node import BaseDecisionEnum
from src.settings import Settings


class Context(BaseModel):
    query: str
    history: list[ChatCompletionMessageParam] = Field(default_factory=list)
    decision: BaseDecisionEnum | None = None
    settings: Settings
    output: str | None = None
    documents: list[str] | None = None
    role: RolesEnum

    @property
    def llm_client(self) -> AsyncOpenAI:
        return get_llm_client(self.settings)

    @property
    def encoder_client(self) -> AsyncOpenAI:
        return get_llm_client(self.settings)

    @property
    def qdrant_client(self) -> AsyncQdrantClient:
        return get_qdrant_client(self.settings)

    @property
    def langfuse_client(self) -> Langfuse:
        return get_client()
