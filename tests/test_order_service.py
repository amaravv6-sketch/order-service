# from decimal import Decimal

# import pytest

# from app.services.order_service import (
#     CreateOrderRequest,
#     InvalidOrderError,
#     create_order,
# )


# def test_create_order_successfully() -> None:
#     request = CreateOrderRequest(
#         product_id="p-100",
#         price=Decimal("250"),
#         quantity=3,
#     )

#     order = create_order(request)

#     assert order.product_id == "p-100"
#     assert order.price == Decimal("250")
#     assert order.quantity == 3
#     assert order.total == Decimal("750")


# def test_create_order_rejects_empty_product_id() -> None:
#     request = CreateOrderRequest(
#         product_id="",
#         price=Decimal("250"),
#         quantity=3,
#     )

#     with pytest.raises(InvalidOrderError):
#         create_order(request)


# def test_create_order_rejects_whitespace_product_id() -> None:
#     request = CreateOrderRequest(
#         product_id="   ",
#         price=Decimal("250"),
#         quantity=3,
#     )

#     with pytest.raises(InvalidOrderError):
#         create_order(request)


# def test_create_order_rejects_zero_price() -> None:
#     request = CreateOrderRequest(
#         product_id="p-200",
#         price=Decimal("0"),
#         quantity=3,
#     )

#     with pytest.raises(InvalidOrderError):
#         create_order(request)


# def test_create_order_rejects_zero_quantity() -> None:
#     request = CreateOrderRequest(
#         product_id="p-200",
#         price=Decimal("250"),
#         quantity=0,
#     )

#     with pytest.raises(InvalidOrderError):
#         create_order(request)