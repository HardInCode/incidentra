"""
SME-Guard Vulnerable Web App (vuln-web)
A deliberately vulnerable Flask app for testing SME-Guard detection.
DO NOT DEPLOY TO PRODUCTION.
"""
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import sqlite3
import os
import json
import time
from collections import defaultdict

app = Flask(__name__)
DB_PATH = 'vuln.db'

# Must match backend BLOCKED_IPS_JSON_PATH (local: ../vuln-web/logs/blocked_ips.json).
BLOCKED_IPS_FILE = os.getenv('BLOCKED_IPS_JSON', 'logs/blocked_ips.json')
RATE_LIMITED_FILE = os.getenv('RATE_LIMITED_JSON', 'logs/rate_limited.json')
RATE_LIMIT_MAX = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 10))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))

# In-memory request counters for rate limiting
_request_log: dict = defaultdict(list)


def _load_json_file(path):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


@app.before_request
def enforce_security():
    """BUG 3 & BUG 4 FIX: Enforce IP blocking and rate limiting from shared JSON files."""
    ip = request.remote_addr

    # Skip enforcement for /api/status
    if request.path == '/api/status':
        return

    # BUG 3 FIX: Check blocked IPs
    blocked_data = _load_json_file(BLOCKED_IPS_FILE)
    blocked_list = blocked_data.get('blocked', [])
    if ip in blocked_list:
        return render_template_string(FORBIDDEN_HTML, ip=ip), 403

    # BUG 4 FIX: Check rate limiting (per-IP overrides in JSON "limits")
    rate_data = _load_json_file(RATE_LIMITED_FILE)
    rate_limited_list = rate_data.get('rate_limited', [])
    if ip in rate_limited_list:
        limits = rate_data.get('limits') or {}
        override = limits.get(ip) if isinstance(limits, dict) else None
        window = RATE_LIMIT_WINDOW
        max_req = RATE_LIMIT_MAX
        if isinstance(override, dict):
            if 'window_seconds' in override:
                window = int(override['window_seconds'])
            if 'max_requests' in override:
                max_req = int(override['max_requests'])
        now = time.time()
        _request_log[ip] = [t for t in _request_log[ip] if now - t < window]
        _request_log[ip].append(now)
        count = len(_request_log[ip])
        if count > max_req:
            retry_after = window - int(now - _request_log[ip][0])
            response = render_template_string(
                TOO_MANY_REQUESTS_HTML, ip=ip, limit=max_req, retry=max(retry_after, 1),
            ), 429
            return response


FORBIDDEN_HTML = """
<!DOCTYPE html><html><head><title>403 Forbidden - SME-Guard</title>
<style>body{font-family:sans-serif;background:#0a0e1a;color:#e8eaf6;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.box{text-align:center;padding:3rem;border:1px solid rgba(255,23,68,0.3);border-radius:16px;background:rgba(255,23,68,0.05);}
h1{color:#ff1744;font-size:3rem;margin:0;}p{color:#8892a4;}</style></head>
<body><div class="box"><h1>🔒 403</h1><h2>Access Forbidden</h2>
<p>Your IP address <strong style="color:#ff6d00;font-family:monospace">{{ ip }}</strong> has been blocked by SME-Guard.</p>
<p>Contact your system administrator if you believe this is an error.</p></div></body></html>
"""

TOO_MANY_REQUESTS_HTML = """
<!DOCTYPE html><html><head><title>429 Too Many Requests - SME-Guard</title>
<style>body{font-family:sans-serif;background:#0a0e1a;color:#e8eaf6;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.box{text-align:center;padding:3rem;border:1px solid rgba(255,214,0,0.3);border-radius:16px;background:rgba(255,214,0,0.05);}
h1{color:#ffd600;font-size:3rem;margin:0;}p{color:#8892a4;}</style></head>
<body><div class="box"><h1>⏱ 429</h1><h2>Too Many Requests</h2>
<p>Your IP <strong style="color:#ff6d00;font-family:monospace">{{ ip }}</strong> is rate limited to <strong>{{ limit }} req/min</strong>.</p>
<p>Please retry in <strong>{{ retry }}s</strong>.</p></div></body></html>
"""


@app.route('/api/status')
def api_status():
    """BUG 4 FIX: Return current blocked and rate-limited IPs for backend verification."""
    blocked_data = _load_json_file(BLOCKED_IPS_FILE)
    rate_data = _load_json_file(RATE_LIMITED_FILE)
    return jsonify({
        'blocked_ips': blocked_data.get('blocked', []),
        'rate_limited_ips': rate_data.get('rate_limited', []),
        'blocked_ips_updated': blocked_data.get('updated_at'),
        'rate_limited_updated': rate_data.get('updated_at'),
    })

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT, role TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY, name TEXT, price REAL, description TEXT
    )''')
    # Seed data
    conn.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','secret123','admin@company.com','admin')")
    conn.execute("INSERT OR IGNORE INTO users VALUES (2,'john','pass1234','john@company.com','user')")
    conn.execute("INSERT OR IGNORE INTO products VALUES (1,'Product A',99.99,'A great product')")
    conn.execute("INSERT OR IGNORE INTO products VALUES (2,'Product B',149.99,'Another product')")
    conn.commit()
    conn.close()

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SME Shop - {{ title }}</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #333; }
.nav { background: #2563eb; color: #fff; padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
.nav h1 { font-size: 1.3rem; font-weight: 700; }
.nav a { color: #93c5fd; text-decoration: none; margin-left: 1rem; }
.container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
.card { background: #fff; border-radius: 12px; padding: 2rem; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
.card h2 { margin-bottom: 1rem; color: #1e3a5f; }
form { display: flex; flex-direction: column; gap: 0.75rem; }
input, textarea { padding: 0.65rem 0.85rem; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.95rem; }
button { background: #2563eb; color: #fff; border: none; padding: 0.7rem 1.5rem; border-radius: 8px; cursor: pointer; font-size: 0.95rem; font-weight: 600; }
button:hover { background: #1d4ed8; }
.result { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 1rem; margin-top: 1rem; }
.error { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 1rem; margin-top: 1rem; color: #dc2626; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.6rem 1rem; border-bottom: 1px solid #e5e7eb; }
th { background: #f9fafb; font-weight: 600; color: #6b7280; font-size: 0.8rem; text-transform: uppercase; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-blue { background: #dbeafe; color: #1d4ed8; }
.warning { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; font-size: 0.85rem; color: #92400e; }
</style>
</head>
<body>
<div class="nav">
  <h1>🛒 SME Shop</h1>
  <div>
    <a href="/">Home</a>
    <a href="/login">Login</a>
    <a href="/search">Search</a>
    <a href="/profile">Profile</a>
    <a href="/files">Files</a>
  </div>
</div>
<div class="container">
{{ content | safe }}
</div>
</body>
</html>
"""


def render(title, content):
    return render_template_string(BASE_HTML, title=title, content=content)


@app.route('/')
def index():
    return render("Home", """
    <div class="card">
        <h2>Welcome to SME Shop</h2>
        <p style="color:#6b7280; margin-top:0.5rem">This is a <strong>deliberately vulnerable</strong> web application for testing SME-Guard security monitoring.</p>
    </div>
    <div class="warning">
        ⚠️ This app is intentionally vulnerable. It is for demo/testing purposes ONLY. Do not use in production.
    </div>
    <div class="card">
        <h2>Test Endpoints</h2>
        <table>
            <tr><th>Endpoint</th><th>Vulnerability</th><th>Test Payload</th></tr>
            <tr><td>/login</td><td>SQL Injection</td><td>username: admin' OR '1'='1</td></tr>
            <tr><td>/search</td><td>XSS + SQLi</td><td>q: &lt;script&gt;alert(1)&lt;/script&gt;</td></tr>
            <tr><td>/profile</td><td>XSS Reflected</td><td>name param: &lt;img onerror=alert(1) src=x&gt;</td></tr>
            <tr><td>/files</td><td>Path Traversal</td><td>file: ../../etc/passwd</td></tr>
            <tr><td>/cmd</td><td>Command Injection</td><td>cmd: ; whoami</td></tr>
            <tr><td>/login (repeat)</td><td>Brute Force</td><td>10+ attempts trigger detection</td></tr>
        </table>
    </div>
    """)


@app.route('/login', methods=['GET', 'POST'])
def login():
    result = ''
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        # VULNERABLE: SQL Injection
        try:
            conn = sqlite3.connect(DB_PATH)
            query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
            cursor = conn.execute(query)
            user = cursor.fetchone()
            conn.close()
            if user:
                result = f'<div class="result">✅ Login successful! Welcome, {user[1]} ({user[4]})</div>'
            else:
                result = '<div class="error">❌ Invalid credentials</div>'
        except Exception as e:
            result = f'<div class="error">DB Error: {e}</div>'

    return render("Login", f"""
    <div class="card">
        <h2>🔐 Login</h2>
        <p style="color:#6b7280;margin-bottom:1rem;font-size:0.85rem">Vulnerable to SQL Injection. Try: admin' OR '1'='1' --</p>
        <form method="post">
            <input name="username" placeholder="Username" value="{request.form.get('username','')}">
            <input name="password" type="text" placeholder="Password (shown for demo)">
            <button type="submit">Login</button>
        </form>
        {result}
    </div>
    """)


@app.route('/search')
def search():
    q = request.args.get('q', '')
    results_html = ''
    if q:
        try:
            conn = sqlite3.connect(DB_PATH)
            # VULNERABLE: SQL Injection + XSS (output not escaped)
            query = f"SELECT * FROM products WHERE name LIKE '%{q}%' OR description LIKE '%{q}%'"
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conn.close()
            if rows:
                rows_html = ''.join([f'<tr><td>{r[1]}</td><td>${r[2]}</td><td>{r[3]}</td></tr>' for r in rows])
                results_html = f'<div class="result"><table><tr><th>Name</th><th>Price</th><th>Description</th></tr>{rows_html}</table></div>'
            else:
                results_html = f'<div class="result">No results for: {q}</div>'  # XSS: q is not escaped
        except Exception as e:
            results_html = f'<div class="error">Error: {e}</div>'

    return render("Search", f"""
    <div class="card">
        <h2>🔍 Product Search</h2>
        <p style="color:#6b7280;margin-bottom:1rem;font-size:0.85rem">Vulnerable to SQL Injection and XSS. Try: &lt;script&gt;alert(document.cookie)&lt;/script&gt;</p>
        <form method="get">
            <input name="q" placeholder="Search products..." value="{q}">
            <button type="submit">Search</button>
        </form>
        {results_html}
    </div>
    """)


@app.route('/profile')
def profile():
    # VULNERABLE: Reflected XSS
    name = request.args.get('name', 'Guest')
    return render("Profile", f"""
    <div class="card">
        <h2>👤 User Profile</h2>
        <p style="color:#6b7280;margin-bottom:1rem;font-size:0.85rem">Vulnerable to Reflected XSS. Try: ?name=&lt;img src=x onerror=alert(1)&gt;</p>
        <p>Hello, {name}!</p>
        <form method="get">
            <input name="name" placeholder="Your name" value="{name}">
            <button type="submit">Update</button>
        </form>
    </div>
    """)


@app.route('/files')
def files():
    # VULNERABLE: Path Traversal
    filename = request.args.get('file', '')
    content = ''
    if filename:
        try:
            # Simulated path traversal (reads from safe sandbox directory in demo)
            safe_base = os.path.join(os.getcwd(), 'safe_files')
            os.makedirs(safe_base, exist_ok=True)
            filepath = os.path.join(safe_base, filename.replace('../', ''))
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
            else:
                content = f'[Simulated] Would read: {filename}'
        except Exception as e:
            content = str(e)

    return render("Files", f"""
    <div class="card">
        <h2>📁 File Browser</h2>
        <p style="color:#6b7280;margin-bottom:1rem;font-size:0.85rem">Vulnerable to Path Traversal. Try: ?file=../../etc/passwd</p>
        <form method="get">
            <input name="file" placeholder="Filename..." value="{filename}">
            <button type="submit">Read File</button>
        </form>
        {'<div class="result"><pre>' + content + '</pre></div>' if content else ''}
    </div>
    """)


@app.route('/cmd')
def cmd():
    # VULNERABLE: Command Injection (simulated - safe in demo)
    cmd_input = request.args.get('cmd', '')
    output = ''
    if cmd_input:
        output = f'[Simulated] Would execute: {cmd_input}\nThis is sandboxed for demo safety.'

    return render("Command", f"""
    <div class="card">
        <h2>⚙️ System Command</h2>
        <p style="color:#6b7280;margin-bottom:1rem;font-size:0.85rem">Vulnerable to Command Injection. Try: ?cmd=; cat /etc/passwd</p>
        <form method="get">
            <input name="cmd" placeholder="Command..." value="{cmd_input}">
            <button type="submit">Execute</button>
        </form>
        {'<div class="result"><pre>' + output + '</pre></div>' if output else ''}
    </div>
    """)


@app.after_request
def log_request(response):
    """Log all requests in Combined Log Format for SME-Guard to monitor.
    Includes POST form data for sensitive endpoints so detection engine can see SQLi in login body.
    """
    import datetime
    post_data = ''
    if request.method == 'POST' and request.form:
        params = []
        for key, value in request.form.items():
            params.append(f'{key}={str(value)[:200]}')
        post_data = ' POST_DATA:' + '&'.join(params)

    log_line = (
        f'{request.remote_addr} - - '
        f'[{datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")}] '
        f'"{request.method} {request.full_path.rstrip("?")} HTTP/1.1" '
        f'{response.status_code} {response.content_length or 0} '
        f'"-" "{request.user_agent.string}"{post_data}'
    )
    LOG_FILE = os.getenv('VULN_LOG_FILE', 'logs/access.log')
    os.makedirs(os.path.dirname(LOG_FILE) if os.path.dirname(LOG_FILE) else '.', exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')
    return response


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.getenv('VULN_PORT', 5050)), debug=False)
