import logging
import traceback
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware import Middleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.requests import Request
from langfuse import Langfuse, propagate_attributes
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import HTMLResponse, JSONResponse, Response
from pydantic_ai.agent import Agent

from src.dependencies import get_settings
from src.logging_config import session_id_var, setup_logging
from src.pipeline.config import CHAT_BOT
from src.pipeline.context import Context
from src.pipeline.orchestrator import Orchestrator
from src.prometheus_config import PROMETHEUS_REGISTRY
from src.prometheus_middleware import PrometheusMiddleware
from src.schemes import ChatRequest, ChatResponse
from src.settings import Settings

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Agent.instrument_all()  # init pydantic ai agent for langfuse https://langfuse.com/integrations/frameworks/pydantic-ai
    yield

app = FastAPI(
    title="LLM Service API",
    description="API for interacting with Large Language Models",
    middleware=[Middleware(PrometheusMiddleware)],
    docs_url=None,
    lifespan=lifespan,
)

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"Unhandled exception processing {request.url}:\n{tb}")

    return JSONResponse(
        status_code=500,
        content={"error": str(exc)},  # return exception message
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post(
    "/chat",
    tags=["chat"],
)
async def chat(
    request: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    """
    Chat endpoint to process user queries and return responses.
    """
    session_id_var.set(request.session_id)
    logger.info("Received chat request: %s ", request.model_dump())
    orchestrator = Orchestrator(CHAT_BOT)
    context = Context(
        query=request.query,
        history=request.history or [],
        settings=settings,
        role=request.role,
    )
    langfuse_client = Langfuse(
        public_key=settings.langfuse.public_key,
        secret_key=settings.langfuse.secret_key,
        environment=settings.langfuse.environment,
        base_url=str(settings.langfuse.base_url),
    )

    with langfuse_client.start_as_current_observation(
        name="chat_interaction",
        input=request.model_dump(),
    ) as observation:
        with propagate_attributes(
            session_id=request.session_id,
            environment=settings.langfuse.environment,
            metadata={
                "role": request.role,
            },
        ):
            try:
                response = await orchestrator.execute(context)
            except Exception as e:
                logger.error(f"Error processing chat request: {e}")
                observation.update(
                    level="ERROR",
                    status_message=str(e),
                )
                raise
        observation.update(
            output={"response": response},
        )
    logger.info("Chat response: %s", response)
    return ChatResponse(content=response)


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(PROMETHEUS_REGISTRY), media_type=CONTENT_TYPE_LATEST
    )


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,  # type: ignore[arg-type]
        title=app.title,
        swagger_favicon_url="/favicon.ico",
    )


# @app.get("/favicon.ico", include_in_schema=False)
# async def get_favicon() -> FileResponse:
#     path = Path(__file__).parent / "static" / "icon.ico"
#     return FileResponse(path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
