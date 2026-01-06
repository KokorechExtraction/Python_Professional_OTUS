from dataclasses import dataclass


@dataclass(frozen=True)
class OrderLineDTO:
    product_id: int
    qty: int


@dataclass(frozen=True)
class PlaceOrderCommand:
    customer_id: int
    lines: list[OrderLineDTO]

