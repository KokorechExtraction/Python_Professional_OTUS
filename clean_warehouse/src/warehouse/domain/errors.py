class DomainError(Exception):
    pass


class OutOfStockError(DomainError):
    pass


class NotFoundError(DomainError):
    pass
