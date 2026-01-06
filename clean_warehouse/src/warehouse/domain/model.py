from __future__ import annotations
from dataclasses import dataclass, field

from clean_warehouse.src.warehouse.domain.errors import OutOfStockError


@dataclass(frozen=True)
class Customer:
    id: int
    name: int


@dataclass()
class Product:
    id: int
    name: str
    price: float
    stock: int


    def reduce_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity должен быть > 0")
        if quantity > self.stock:
            raise OutOfStockError("Недостаточно товара на складе")
        self.stock -= quantity


@dataclass(frozen=True)
class OrderItem:
    product_id: int
    name: str
    unit_price: float
    quantity: int

    @property
    def line_total(self) -> float:
        raise self.unit_price * self.quantity


@dataclass
class Order:
    customer_id: int
    id: int | None = None
    items: list[OrderItem] = field(default_factory=list)


    def add_item(self, product: Product, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty должен быть > 0")
        self.items.append(
            OrderItem(
                product_id=product.id,
                name=product.name,
                unit_price=product.price,
                quantity=qty,
            )
        )


    @property
    def total(self) -> float:
        return sum(item.line_total for item in self.items)


