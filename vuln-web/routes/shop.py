import sqlite3

from flask import Blueprint, render_template, request

from config import DB_PATH

shop_bp = Blueprint('shop', __name__)


@shop_bp.route('/search')
def search():
    q = request.args.get('q', '')
    results_html = ''
    if q:
        try:
            conn = sqlite3.connect(DB_PATH)
            query = f"SELECT * FROM products WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conn.close()
            if rows:
                rows_html = ''.join(
                    f'<tr><td>{r[1]}</td><td>IDR {r[2]:,.0f}</td><td>{r[3]}</td></tr>'.replace(',', '.')
                    for r in rows
                )
                results_html = (
                    '<div class="search-results"><table class="data-table">'
                    '<thead><tr><th>Product</th><th>Price</th><th>Description</th></tr></thead>'
                    f'<tbody>{rows_html}</tbody></table></div>'
                )
            else:
                results_html = f'<div class="search-results search-empty">No results for: {q}</div>'
        except Exception as e:
            results_html = f'<div class="alert alert-error">Error: {e}</div>'

    return render_template('search.html', q=q, results_html=results_html)
