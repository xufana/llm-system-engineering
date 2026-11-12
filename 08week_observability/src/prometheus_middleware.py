import time
from typing import ClassVar

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.prometheus_config import PPROMETHEUS_METRIC_PREFIX, PROMETHEUS_REGISTRY

REQUEST_COUNT = Counter(
    f"{PPROMETHEUS_METRIC_PREFIX}http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
    registry=PROMETHEUS_REGISTRY,
)

REQUEST_LATENCY = Histogram(
    f"{PPROMETHEUS_METRIC_PREFIX}http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "path"],
    registry=PROMETHEUS_REGISTRY,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Starlette-compatible Prometheus middleware that can be registered via

        app = FastAPI(middleware=[Middleware(PrometheusMiddleware)])

    It tracks request count and latency, grouped by:
      - HTTP method
      - Resolved route path template
      - Response status code

    `/metrics` is ignored to avoid recursive scraping noise.
    """

    IGNORE_PATHS: ClassVar[set[str]] = {"/metrics", "/health"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            path = route.path
        else:
            path = request.url.path

        # Skip ignored endpoints
        if path in self.IGNORE_PATHS:
            return await call_next(request)

        method = request.method

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            latency = time.perf_counter() - start_time

            REQUEST_COUNT.labels(method, path, str(status_code)).inc()
            REQUEST_LATENCY.labels(method, path).observe(latency)

        return response