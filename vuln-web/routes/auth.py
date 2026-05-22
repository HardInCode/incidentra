import sqlite3

from flask import Blueprint, render_template, request

from config import DB_PATH

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    result = ''
    username = request.form.get('username', '') if request.method == 'POST' else ''
    if request.method == 'POST':
        password = request.form.get('password', '')
        try:
            conn = sqlite3.connect(DB_PATH)
            query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
            cursor = conn.execute(query)
            user = cursor.fetchone()
            conn.close()
            if user:
                result = (
                    '<div class="alert alert-success">'
                    f'Signed in. Welcome, <strong>{user[1]}</strong> '
                    f'(<span class="mono">{user[4]}</span>)</div>'
                )
            else:
                result = '<div class="alert alert-error">Invalid credentials.</div>'
        except Exception as e:
            result = f'<div class="alert alert-error">DB Error: {e}</div>'

    return render_template('login.html', result=result, username=username)
