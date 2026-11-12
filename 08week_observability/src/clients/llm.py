from typing import Any

from langfuse import get_client
from langfuse.model import PromptClient
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.settings import APIModelConfig, Settings


def _get_client(model_config: APIModelConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=model_config.key,
        base_url=str(model_config.base_url),
        timeout=model_config.timeout,
        max_retries=model_config.max_retries,
    )


def get_llm_client(settings: Settings) -> AsyncOpenAI:
    return _get_client(settings.llm)


def get_embedder_client(settings: Settings) -> AsyncOpenAI:
    return _get_client(settings.embedder)


async def get_chat_completion(
    user_query: str,
    settings: Settings,
    system_message: str | None = None,
    llm_client: AsyncOpenAI | None = None,
    params: dict[str, Any] | None = None,
    history: list[ChatCompletionMessageParam] | None = None,
    prompt: PromptClient | None = None,
) -> str:
    if llm_client is None:
        llm_client = get_llm_client(settings)
    with get_client().start_as_current_observation(
        as_type="generation",
        name="llm-generation",
        model=settings.llm.name,
        prompt=prompt,
    ) as observation:
        if prompt:
            messages = prompt.compile(
                query=user_query,
                history=history,
            )
            params = prompt.config | (params or {})
        else:
            messages = [
                {"role": "system", "content": system_message},
                *(history or []),
                {"role": "user", "content": user_query},
            ]
            params = params or {}
        observation.update(
            input=messages,
            model=settings.llm.name,
            model_parameters=params,
        )
        response = await llm_client.chat.completions.create(
            model=settings.llm.name,
            messages=messages,
            **params,
        )
        output = response.choices[0].message.content
        observation.update(
            output=output,
            usage_details=response.usage.model_dump(),
        )
    return output


async def get_embedding(
    text: str | list[str],
    settings: Settings,
    embedder_client: AsyncOpenAI | None = None,
) -> list[list[float]]:
    if embedder_client is None:
        embedder_client = get_embedder_client(settings)

    with get_client().start_as_current_observation(
        as_type="embedding",
        name="embedding-generation",
        input=text,
        model=settings.embedder.name,
    ) as observation:
        response = await embedder_client.embeddings.create(
            model=settings.embedder.name,
            input=text,
        )
        embeddings = [data.embedding[:1024] for data in response.data]
        observation.update(
            output=embeddings,
            usage_details=response.usage.model_dump(),
        )

    return embeddings