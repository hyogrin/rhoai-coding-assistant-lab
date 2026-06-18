import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "cafe_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "cafe_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_ORDERS = Gauge(
    "cafe_active_orders",
    "Number of orders in non-terminal state",
)

ORDERS_TOTAL = Counter(
    "cafe_orders_total",
    "Total orders created",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in ("/metrics", "/health"):
            return await call_next(request)

        method = request.method
        path = self._normalize_path(request.url.path)
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        status = str(response.status_code)

        REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
        REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        parts = path.split("/")
        normalized = []
        for i, part in enumerate(parts):
            if part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)
