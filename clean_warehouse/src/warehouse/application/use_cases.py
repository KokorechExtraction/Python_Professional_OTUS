from __future__ import annotations

from clean_warehouse.src.warehouse.application.dtos import PlaceOrderCommand
from clean_warehouse.src.warehouse.application.uow import UnitOfWork
from clean_warehouse.src.warehouse.domain.errors import NotFoundError
from clean_warehouse.src.warehouse.domain.model import Order


class PlaceOrderUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow


    def execute(self, cmd: PlaceOrderCommand) -> Order:
        with self.uow:
            customer = self.uow.customer.get_by_id(cmd.customer_id)
            if customer is None:
                raise NotFoundError("Покупатель не найден")

            products_ids = [l.product_id for l in cmd.lines]
            products = {p.id: p for p in self.uow.products.list_by_ids(products_ids)}

            order = Order(customer_id=customer.id)

            for line in cmd.lines:
                p = products[line.product_id]
                p.reduce_stock(line.qty)
                order.add_item(p, line.qty)
                self.uow.products.save(p)

            self.uow.orders.add(order)
            self.uow.commit()
            return order
