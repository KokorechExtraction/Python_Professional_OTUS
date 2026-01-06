from __future__ import annotations
from typing import Iterable

from clean_warehouse.src.warehouse.domain.model import Product, Customer, Order


class ProductRepositorySQL:
    def __init__(self, conn):
        self.conn = conn

    def get_by_id(self, product_id: int) -> Product | None:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT id, name, price, stock FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()
        if not row:
            return None
        return Product(id=row[0], name=row[1], price=row[2], stock=row[3])

    def list_by_ids(self, ids: Iterable[int]) -> list[Product]:
        ids = list(ids)
        if not ids:
            return []
        placeholders = ",".join(["?"] * len(ids))
        cur = self.conn.cursor()
        rows = cur.execute(
            f"SELECT id, name, price, stock FROM products WHERE id IN ({placeholders})",
            ids
        ).fetchall()
        return [Product(id=r[0], name=r[1], price=r[2], stock=r[3]) for r in rows]

    def save(self, product: Product) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
            (product.name, product.price, product.stock, product.id),
        )


class CustomerRepositorySQL:
    def __init__(self, conn):
        self.conn = conn

    def get_by_id(self, customer_id: int) -> Customer | None:
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT id, name FROM customers WHERE id = ?",
            (customer_id,)
        ).fetchone()
        if not row:
            return None
        return Customer(id=row[0], name=row[1])


class OrderRepositorySQL:
    def __init__(self, conn):
        self.conn = conn

    def add(self, order: Order) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO orders (customer_id, total) VALUES (?, ?)",
            (order.customer_id, order.total)
        )
        order_id = cur.lastrowid
        order.id = order_id

        for item in order.items:
            cur.execute(
                """
                INSERT INTO order_items (order_id, product_id, name, unit_price, quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, item.product_id, item.name, item.unit_price, item.quantity)
            )