import pytest

from app.application.dtos import PlaceOrderCommand, OrderLineDTO
from app.application.use_cases import PlaceOrderUseCase
from app.domain.models import Product, Customer
from app.domain.errors import OutOfStockError


class InMemoryProductRepo:
    def __init__(self, products):
        self._products = {p.id: p for p in products}

    def get_by_id(self, product_id: int):
        return self._products.get(product_id)

    def list_by_ids(self, ids):
        return [self._products[i] for i in ids if i in self._products]

    def save(self, product: Product):
        self._products[product.id] = product


class InMemoryCustomerRepo:
    def __init__(self, customers):
        self._customers = {c.id: c for c in customers}

    def get_by_id(self, customer_id: int):
        return self._customers.get(customer_id)


class InMemoryOrderRepo:
    def __init__(self):
        self.orders = []

    def add(self, order):
        order.id = len(self.orders) + 1
        self.orders.append(order)


class InMemoryUoW:
    def __init__(self, products, customers):
        self.products = InMemoryProductRepo(products)
        self.customers = InMemoryCustomerRepo(customers)
        self.orders = InMemoryOrderRepo()
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_place_order_reduces_stock_and_saves_order():
    uow = InMemoryUoW(
        products=[Product(id=1, name="A", price=10.0, stock=5)],
        customers=[Customer(id=100, name="Bob")],
    )
    uc = PlaceOrderUseCase(uow)

    cmd = PlaceOrderCommand(customer_id=100, lines=[OrderLineDTO(product_id=1, qty=2)])
    order = uc.execute(cmd)

    assert order.id == 1
    assert order.total == 20.0
    assert uow.products.get_by_id(1).stock == 3
    assert uow.committed is True
    assert len(uow.orders.orders) == 1


def test_place_order_out_of_stock_rolls_back_and_does_not_save_order():
    uow = InMemoryUoW(
        products=[Product(id=1, name="A", price=10.0, stock=1)],
        customers=[Customer(id=100, name="Bob")],
    )
    uc = PlaceOrderUseCase(uow)

    cmd = PlaceOrderCommand(customer_id=100, lines=[OrderLineDTO(product_id=1, qty=2)])

    with pytest.raises(OutOfStockError):
        uc.execute(cmd)

    assert uow.rolled_back is True
    assert len(uow.orders.orders) == 0
    assert uow.products.get_by_id(1).stock == 1  # не изменилось
