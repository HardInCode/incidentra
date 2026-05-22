"""SQLite helpers and seed data for SME Shop."""
import sqlite3

from config import DB_PATH

PRODUCTS_SEED = [
    (1, 'Gayo Arabica Coffee', 89_000, 'Single-origin Aceh beans, medium roast. 250g bag.'),
    (2, 'Organic Jasmine Tea', 45_000, 'Loose leaf, pesticide-free. 100g pack.'),
    (3, 'Kalimantan Forest Honey', 125_000, 'Raw, unheated. 350ml bottle.'),
    (4, 'Spicy Cassava Chips', 18_500, 'Local snack, medium heat. 150g.'),
    (5, 'Handmade Canvas Tote', 159_000, 'Screen-printed by local artisans. Fits 14" laptop.'),
    (6, 'Natural Bar Soap Set', 32_000, 'Coconut oil + citrus. Pack of 3 bars.'),
    (7, 'Homemade Chili Garlic Sauce', 28_000, 'No preservatives — refrigerate after opening.'),
    (8, 'Lavender Essential Oil', 75_000, 'For diffuser use; dilute before skin contact. 10ml.'),
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT, role TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT
    )''')
    conn.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','secret123','admin@company.com','admin')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (2,'john','pass1234','john@company.com','user')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (3,'guest','guest','guest@shop.local','user')")
    for row in PRODUCTS_SEED:
        conn.execute(
            'INSERT OR IGNORE INTO products VALUES (?,?,?,?)',
            row,
        )
    conn.commit()
    conn.close()


def fetch_products(limit=None):
    conn = get_connection()
    if limit:
        cursor = conn.execute('SELECT id, name, price, description FROM products ORDER BY id LIMIT ?', (limit,))
    else:
        cursor = conn.execute('SELECT id, name, price, description FROM products ORDER BY id')
    rows = cursor.fetchall()
    conn.close()
    return rows
