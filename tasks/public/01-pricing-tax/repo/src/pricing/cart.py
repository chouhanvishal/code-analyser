from dataclasses import dataclass


@dataclass
class Item:
    name: str
    price: float
    qty: int = 1


def subtotal(items):
    return sum(i.price * i.qty for i in items)


def total(items, tax_rate):
    return round(subtotal(items) * tax_rate, 2)
