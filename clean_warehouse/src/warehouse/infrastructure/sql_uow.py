from __future__ import annotations

from clean_warehouse.src.warehouse.application.uow import UnitOfWork
from clean_warehouse.src.warehouse.infrastructure.sql_repositories import (
    ProductRepositorySQL,
    CustomerRepositorySQL,
    OrderRepositorySQL,
)


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, connection):
        self.connection = connection
        self.products = ProductRepositorySQL(self.connection)
        self.customers = CustomerRepositorySQL(self.connection)
        self.orders = OrderRepositorySQL(self.connection)

    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()
