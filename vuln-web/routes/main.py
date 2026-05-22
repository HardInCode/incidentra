from flask import Blueprint, render_template

from db import fetch_products

main_bp = Blueprint('main', __name__)

# Decorative product card colors (CSS only)
CARD_THEMES = [
    'card-theme-1', 'card-theme-2', 'card-theme-3', 'card-theme-4',
    'card-theme-5', 'card-theme-6', 'card-theme-7', 'card-theme-8',
]


def _product_cards(products):
    items = []
    for i, row in enumerate(products):
        pid, name, price, desc = row
        theme = CARD_THEMES[i % len(CARD_THEMES)]
        items.append({
            'id': pid,
            'name': name,
            'price': price,
            'description': desc,
            'theme': theme,
        })
    return items


@main_bp.route('/')
def index():
    featured = _product_cards(fetch_products(4))
    return render_template('home.html', featured=featured)


@main_bp.route('/catalog')
def catalog():
    products = _product_cards(fetch_products())
    return render_template('catalog.html', products=products)
