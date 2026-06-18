import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import APP_NAME, APP_VERSION
from app.database import init_db, SessionLocal
from app.models import MenuItem, Customer, MenuCategory
from app.routes import menu, orders, customers
from app.middleware import MetricsMiddleware


def _setup_tracing():
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otel_endpoint:
        return
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    resource = Resource.create({"service.name": "cafe-order-system", "service.version": APP_VERSION})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return FastAPIInstrumentor


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _seed_data()
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(MetricsMiddleware)

_instrumentor = _setup_tracing()
if _instrumentor:
    _instrumentor.instrument_app(app)

app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(customers.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": APP_NAME, "version": APP_VERSION}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/stats")
def get_stats():
    from app.services.inventory_service import get_popular_items, get_category_summary

    db = SessionLocal()
    try:
        return {
            "popular_items": get_popular_items(db),
            "category_summary": get_category_summary(db),
        }
    finally:
        db.close()


def _seed_data():
    """Populate initial menu and test customers on first run."""
    db = SessionLocal()
    try:
        if db.query(MenuItem).count() > 0:
            return

        menu_items = [
            MenuItem(name="아메리카노", category=MenuCategory.COFFEE, price=4500, description="깊고 진한 에스프레소에 물을 더한 클래식", calories=10),
            MenuItem(name="카페라떼", category=MenuCategory.COFFEE, price=5000, description="부드러운 우유와 에스프레소의 조화", calories=180, allergens="우유"),
            MenuItem(name="바닐라라떼", category=MenuCategory.COFFEE, price=5500, description="바닐라 시럽이 들어간 달콤한 라떼", calories=250, allergens="우유"),
            MenuItem(name="콜드브루", category=MenuCategory.COFFEE, price=5000, description="24시간 저온 추출한 부드러운 커피", calories=5),
            MenuItem(name="카푸치노", category=MenuCategory.COFFEE, price=5000, description="풍성한 우유 거품이 올라간 에스프레소", calories=120, allergens="우유"),
            MenuItem(name="녹차라떼", category=MenuCategory.TEA, price=5500, description="유기농 말차와 우유의 조합", calories=200, allergens="우유"),
            MenuItem(name="얼그레이", category=MenuCategory.TEA, price=4000, description="베르가못 향이 은은한 홍차", calories=0),
            MenuItem(name="캐모마일", category=MenuCategory.TEA, price=4000, description="심신 안정에 좋은 허브티", calories=0),
            MenuItem(name="망고스무디", category=MenuCategory.SMOOTHIE, price=6000, description="신선한 망고와 요거트 블렌딩", calories=280, allergens="우유"),
            MenuItem(name="베리스무디", category=MenuCategory.SMOOTHIE, price=6000, description="블루베리, 딸기, 라즈베리 믹스", calories=220),
            MenuItem(name="크루아상", category=MenuCategory.BAKERY, price=4000, description="버터 풍미 가득한 프랑스식 페이스트리", calories=350, allergens="밀,우유,계란"),
            MenuItem(name="베이글", category=MenuCategory.BAKERY, price=3500, description="쫄깃한 식감의 플레인 베이글", calories=270, allergens="밀"),
            MenuItem(name="블루베리머핀", category=MenuCategory.BAKERY, price=3800, description="블루베리가 가득한 촉촉한 머핀", calories=380, allergens="밀,우유,계란"),
            MenuItem(name="클럽샌드위치", category=MenuCategory.SANDWICH, price=7000, description="치킨, 베이컨, 신선한 야채의 조합", calories=520, allergens="밀,계란"),
            MenuItem(name="에그샌드위치", category=MenuCategory.SANDWICH, price=5500, description="부드러운 계란 샐러드와 토스트", calories=380, allergens="밀,계란,우유"),
        ]

        customers_data = [
            Customer(employee_id="EMP001", name="김민수", department="개발팀", email="minsu.kim@corp.internal"),
            Customer(employee_id="EMP002", name="이지영", department="디자인팀", email="jiyoung.lee@corp.internal"),
            Customer(employee_id="EMP003", name="박준호", department="인프라팀", email="junho.park@corp.internal"),
            Customer(employee_id="EMP004", name="최서연", department="QA팀", email="seoyeon.choi@corp.internal"),
            Customer(employee_id="EMP005", name="정다은", department="개발팀", email="daeun.jung@corp.internal"),
        ]

        db.add_all(menu_items)
        db.add_all(customers_data)
        db.commit()
    finally:
        db.close()
