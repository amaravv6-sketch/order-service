import os
from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache.redis_client import get_redis_client
from app.security.auth import create_access_token

from app.events.order_publisher import get_order_event_publisher

import json

from app.db.models import OutboxEventModel

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "INFO"

os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
os.environ["ORDER_CREATED_TOPIC"] = "orders.created"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ISSUER"] = "order-service"
os.environ["JWT_AUDIENCE"] = "order-service-api"

from app.db.models import Base
from app.db.session import get_db
from app.main import app


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    def ping(self) -> bool:
        return True

fake_redis = FakeRedis()

def override_get_redis_client() -> FakeRedis:
    return fake_redis


app.dependency_overrides[get_redis_client] = override_get_redis_client

class FakeOrderEventPublisher:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish_order_created(
        self,
        *,
        order_id: int,
        product_id: str,
        price: Decimal,
        quantity: int,
        total: Decimal,
    ) -> None:
        self.events.append(
            {
                "event_id": f"test-event-{order_id}",
                "event_type": "OrderCreated",
                "order_id": order_id,
                "product_id": product_id,
                "price": str(price),
                "quantity": quantity,
                "total": str(total),
            }
        )

fake_event_publisher = FakeOrderEventPublisher()

def override_get_order_event_publisher() -> FakeOrderEventPublisher:
    return fake_event_publisher


app.dependency_overrides[get_order_event_publisher] = override_get_order_event_publisher




def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def auth_headers(roles: list[str] | None = None) -> dict[str, str]:
    token = create_access_token(
        subject="test-user",
        roles=roles or ["order_reader", "order_writer"],
    )

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    fake_redis.store.clear()
    fake_event_publisher.events.clear()

    yield


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "order-service"
    assert response.json()["environment"] == "test"


def test_create_order_successfully() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "250",
            "quantity": 3,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] > 0
    assert body["product_id"] == "p-100"
    assert body["quantity"] == 3
    assert Decimal(str(body["price"])) == Decimal("250")
    assert Decimal(str(body["total"])) == Decimal("750")


def test_create_order_rejects_zero_price() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "0",
            "quantity": 3,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_create_order_rejects_zero_quantity() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "250",
            "quantity": 0,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_create_order_rejects_blank_product_id() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "   ",
            "price": "250",
            "quantity": 3,
        },
        headers=auth_headers(),
    )

    assert response.status_code in (400, 422)


def test_request_id_header_is_returned() -> None:
    response = client.get(
        "/health",
        headers=auth_headers().update({"X-Request-ID": "test-request-123"}),
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"


def test_get_order_by_id_successfully() -> None:
    create_response = client.post(
        "/orders",
        json={
            "product_id": "p-200",
            "price": "100",
            "quantity": 2,
        },
        headers=auth_headers(),
    )

    assert create_response.status_code == 201

    created_order = create_response.json()
    order_id = created_order["id"]

    get_response = client.get(f"/orders/{order_id}")

    assert get_response.status_code == 200

    body = get_response.json()

    assert body["id"] == order_id
    assert body["product_id"] == "p-200"
    assert body["quantity"] == 2
    assert Decimal(str(body["price"])) == Decimal("100")
    assert Decimal(str(body["total"])) == Decimal("200")


def test_get_order_by_id_returns_404_when_not_found() -> None:
    response = client.get("/orders/999999", headers=auth_headers(),)

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_order_by_id_rejects_invalid_id() -> None:
    response = client.get("/orders/0", headers=auth_headers(),)

    assert response.status_code == 422


def test_list_orders_returns_orders() -> None:
    client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "250",
            "quantity": 3,
        },
        headers=auth_headers(),
    )

    client.post(
        "/orders",
        json={
            "product_id": "p-200",
            "price": "100",
            "quantity": 2,
        },
        headers=auth_headers(),
    )

    response = client.get("/orders", headers=auth_headers(),)

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2
    assert body[0]["product_id"] == "p-100"
    assert body[1]["product_id"] == "p-200"


def test_list_orders_filters_by_product_id() -> None:
    client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "250",
            "quantity": 3,
        },
        headers=auth_headers(),
    )

    client.post(
        "/orders",
        json={
            "product_id": "p-200",
            "price": "100",
            "quantity": 2,
        },
        headers=auth_headers(),
    )

    response = client.get("/orders?product_id=p-100", headers=auth_headers(),)

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["product_id"] == "p-100"


def test_list_orders_supports_pagination() -> None:
    client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "250",
            "quantity": 3,
        },
        headers=auth_headers(),
    )

    client.post(
        "/orders",
        json={
            "product_id": "p-200",
            "price": "100",
            "quantity": 2,
        },
        headers=auth_headers(),
    )

    response = client.get("/orders?limit=1&offset=1", headers=auth_headers(),)

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["product_id"] == "p-200"


def test_list_orders_rejects_invalid_limit() -> None:
    response = client.get("/orders?limit=0", headers=auth_headers(),)

    assert response.status_code == 422


def test_list_orders_supports_cursor_pagination() -> None:
    first_response = client.post(
        "/orders",
        json={
            "product_id": "p-100",
            "price": "100",
            "quantity": 1,
        },
        headers=auth_headers(),
    )

    second_response = client.post(
        "/orders",
        json={
            "product_id": "p-200",
            "price": "200",
            "quantity": 1,
        },
        headers=auth_headers(),
    )

    third_response = client.post(
        "/orders",
        json={
            "product_id": "p-300",
            "price": "300",
            "quantity": 1,
        },
        headers=auth_headers(),
    )

    first_order_id = first_response.json()["id"]

    response = client.get(f"/orders?after_id={first_order_id}&limit=2", headers=auth_headers(),)

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 2
    assert body[0]["id"] == second_response.json()["id"]
    assert body[1]["id"] == third_response.json()["id"]


def test_list_orders_rejects_offset_and_after_id_together() -> None:
    response = client.get("/orders?after_id=1&offset=1", headers=auth_headers(),)

    assert response.status_code == 400
    assert response.json()["detail"] == "Use either after_id or offset, not both"


def test_get_order_by_id_uses_cache_after_first_read() -> None:
    create_response = client.post(
        "/orders",
        json={
            "product_id": "p-cache",
            "price": "50",
            "quantity": 2,
        },
        headers=auth_headers(),
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    first_get_response = client.get(f"/orders/{order_id}", headers=auth_headers(),)
    assert first_get_response.status_code == 200

    cache_key = f"order:{order_id}"
    assert cache_key in fake_redis.store

    second_get_response = client.get(f"/orders/{order_id}", headers=auth_headers(),)
    assert second_get_response.status_code == 200
    assert second_get_response.json()["product_id"] == "p-cache"

def test_create_order_creates_outbox_event() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "p-event",
            "price": "125",
            "quantity": 2,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 201

    body = response.json()

    with TestingSessionLocal() as db:
        outbox_events = db.query(OutboxEventModel).all()

    assert len(outbox_events) == 1

    outbox_event = outbox_events[0]
    payload = json.loads(outbox_event.payload)

    assert outbox_event.event_type == "OrderCreated"
    assert outbox_event.topic == "orders.created"
    assert outbox_event.published is False

    assert payload["event_type"] == "OrderCreated"
    assert payload["order_id"] == body["id"]
    assert payload["product_id"] == "p-event"
    assert payload["price"] in ("125", "125.00")
    assert payload["quantity"] == 2
    assert payload["total"] in ("250", "250.00")
    assert "event_id" in payload

# def test_create_order_publishes_order_created_event() -> None:
#     response = client.post(
#         "/orders",
#         json={
#             "product_id": "p-event",
#             "price": "125",
#             "quantity": 2,
#         },
#     )

#     assert response.status_code == 201

#     body = response.json()

#     assert len(fake_event_publisher.events) == 1

#     event = fake_event_publisher.events[0]
#     assert "event_id" in event
#     assert event["event_type"] == "OrderCreated"
#     assert event["order_id"] == body["id"]
#     assert event["product_id"] == "p-event"
#     assert Decimal(str(event["price"])) == Decimal("125")
#     assert event["quantity"] == 2
#     assert Decimal(str(event["total"])) == Decimal("250")


def test_list_orders_requires_authentication() -> None:
    response = client.get("/orders")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing authentication token"


def test_create_order_requires_authentication() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "p-secure",
            "price": "100",
            "quantity": 1,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing authentication token"


def test_create_order_requires_writer_role() -> None:
    response = client.post(
        "/orders",
        json={
            "product_id": "p-secure",
            "price": "100",
            "quantity": 1,
        },
        headers=auth_headers(["order_reader"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing required role: order_writer"


def test_list_orders_allows_reader_role() -> None:
    response = client.get(
        "/orders",
        headers=auth_headers(["order_reader"]),
    )

    assert response.status_code == 200


def test_invalid_token_is_rejected() -> None:
    response = client.get(
        "/orders",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing authentication token"