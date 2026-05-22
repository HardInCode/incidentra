"""Session cart helpers (demo checkout, not real payments)."""
from flask import session

from db import get_connection

CART_KEY = 'cart'


def get_cart_items():
    return session.get(CART_KEY, [])


def cart_count():
    return sum(int(item.get('qty', 1)) for item in get_cart_items())


def add_product(product_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        'SELECT id, name, price FROM products WHERE id = ?',
        (product_id,),
    ).fetchone()
    conn.close()
    if not row:
        return False

    cart = session.get(CART_KEY, [])
    for item in cart:
        if item['id'] == row[0]:
            item['qty'] = int(item.get('qty', 1)) + 1
            session[CART_KEY] = cart
            session.modified = True
            return True

    cart.append({
        'id': row[0],
        'name': row[1],
        'price': row[2],
        'qty': 1,
    })
    session[CART_KEY] = cart
    session.modified = True
    return True


def clear_cart():
    session.pop(CART_KEY, None)
