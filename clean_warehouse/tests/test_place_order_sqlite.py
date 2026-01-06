import sqlite3
import pytest

from app.infrastructure.schema import init_schema
from app.infrastructure.sql_uow import SqlUnitOfWork
from app.application.use_cases import PlaceOrderUseCase
from app.application.dtos import PlaceOrderCommand, OrderLineDTO


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    init_schema(c)

    cur = c.cursor()
    cur.execute("INSERT INTO customers (id, name) VALUES (?, ?)", (1, "Alice"))
    cur.execute("INSERT INTO products (id, name, price, stock) VALUES (?, ?, ?, ?)", (10, "Milk", 2.5, 10))
    cur.execute("INSERT INTO products (id, name, price, stock) VALUES (?, ?, ?, ?)", (11, "Bread", 1.2, 3))
    c.commit()
    return c


def test_place_order_persists_order_and_updates_stock(conn):
    uow = SqlUnitOfWork(conn)
    uc = PlaceOrderUseCase(uow)

    cmd = PlaceOrderCommand(
        customer_id=1,
        lines=[
            OrderLineDTO(product_id=10, qty=4),
            OrderLineDTO(product_id=11, qty=2),
        ]
    )
    order = uc.execute(cmd)

    assert order.id is not None
    assert order.total == 2.5 * 4 + 1.2 * 2

    cur = conn.cursor()
    stock10 = cur.execute("SELECT stock FROM products WHERE id=10").fetchone()[0]
    stock11 = cur.execute("SELECT stock FROM products WHERE id=11").fetchone()[0]
    assert stock10 == 6
    assert stock11 == 1

    orders_count = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    items_count = cur.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    assert orders_count == 1
    assert items_count == 2
