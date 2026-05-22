from flask import Blueprint, redirect, render_template, request, url_for

from cart_utils import add_product, cart_count, clear_cart, get_cart_items

cart_bp = Blueprint('cart', __name__)


@cart_bp.route('/cart')
def view_cart():
    items = get_cart_items()
    total = sum(i['price'] * i.get('qty', 1) for i in items)
    return render_template('cart.html', items=items, total=total)


@cart_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add(product_id):
    add_product(product_id)
    return redirect(request.referrer or url_for('main.catalog'))


@cart_bp.route('/cart/clear', methods=['POST'])
def clear():
    clear_cart()
    return redirect(url_for('cart.view_cart'))
