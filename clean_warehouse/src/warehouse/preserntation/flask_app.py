from flask import Flask, request, jsonify

from clean_warehouse.src.warehouse.application.dtos import PlaceOrderCommand, OrderLineDTO
from clean_warehouse.src.warehouse.application.use_cases import PlaceOrderUseCase
from clean_warehouse.src.warehouse.domain.errors import DomainError, NotFoundError, OutOfStockError
from clean_warehouse.src.warehouse.infrastructure.sql_uow import SqlUnitOfWork

app = Flask(__name__)


def create_app(connection):
    uow = SqlUnitOfWork(connection)
    use_case = PlaceOrderUseCase(uow)

    @app.route("/order", methods=["POST"])
    def place_order():
        data = request.get_json(force=True)

        cmd = PlaceOrderCommand(
            customer_id=int(data["customer_id"]),
            lines=[OrderLineDTO(product_id=int(p["product_id"]), qty=int(p["qty"]))
                   for p in data["products"]]
        )

        try:
            order = use_case.execute(cmd)
        except NotFoundError as e:
            return jsonify({"error": str(e)}), 404
        except OutOfStockError as e:
            return jsonify({"error": str(e)}), 409
        except DomainError as e:
            return jsonify({"error": str(e)}), 400

        return jsonify({"order_id": order.id, "total": order.total}), 201

    return app
