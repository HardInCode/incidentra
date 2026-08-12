# Incidentra — Latihan Sidang Q&A

> **Cara pakai:** Jawab sendiri dulu → buka jawaban → cocokkan dengan file & baris kode di bawah.  
> **Companion doc:** `docs/PEMAHAMAN_PROGRESSIF.md` (§16, Appendix A/B untuk Redis/Celery).

---

## A. Arsitektur & Big Picture

### Q1. Jelaskan alur lengkap dari attacker kirim request ke vuln-web sampai muncul incident di dashboard SOC.

**Jawaban:**

1. Attacker → HTTP request ke **vuln-web** (`vuln-web/`).
2. `app.py` → `before_request` → `enforce_security()` (block/rate-limit) → route handler → `after_request` → `log_request()`.
3. `logging.py` tulis 1 baris NCSA + `POST_DATA` (jika POST) ke **`access.log`** (shared volume `vuln_logs`).
4. Backend **`docker_log_monitor.py`** / `start_monitor()` → **`LogTailer.tail()`** baca baris baru.
5. **`parse_log_line()`** → dict (`ip`, `method`, `path`, `query`, …).
6. **`DetectionEngine.analyze()`** → threat dict atau `None`.
7. Jika threat: **`_process_log_line()`** → dedup → INSERT **`Incident`** PostgreSQL → **`respond()`** block/rate-limit.
8. (Opsional) thread **`_do_reputation_check()`** → AbuseIPDB → `country_code`.
9. Frontend **`Dashboard.js`** poll **`GET /api/dashboard/stats`** → KPI + charts update.

**File / direktori:**

| Langkah | Path |
|---------|------|
| Vuln-web hooks | `vuln-web/app.py` |
| Logging | `vuln-web/middleware/logging.py` |
| Log tail + pipeline | `backend/app/core/log_monitor.py` |
| Parse | `backend/app/core/log_parser.py` |
| Detect | `backend/app/core/detection_engine.py` |
| Respond | `backend/app/core/response_manager.py` |
| Dashboard API | `backend/app/api/dashboard.py` |
| Dashboard UI | `frontend/src/pages/Dashboard.js` |
| Shared volume | `docker-compose.yml` → `vuln_logs` |

**Kode kunci:**

```11:13:backend/app/core/log_monitor.py
Alur lengkap:
  logging.py → access.log → LogTailer → line → _process_log_line
    → parse_log_line → analyze → Incident DB → respond
```

```130:136:backend/app/core/log_monitor.py
    entry = parse_log_line(line)  # ← log_parser.py ② — string → dict
    if not entry:
        return None

    threat = engine.analyze(entry)  # ← detection_engine.py analyze()
    if not threat:
        return None
```

```189:194:backend/app/core/log_monitor.py
    db.session.add(incident)
    db.session.commit()

    responder.respond(threat, incident.id)  # ← response_manager.py
```

---

### Q2. Kenapa vuln-web dan backend SOC dipisah?

**Jawaban:**

- Mirip **production**: aplikasi target (lab shop) terpisah dari sistem monitoring/response (SOC).
- **Red Team** attack vuln-web; **Blue Team** monitor via UI — role jelas.
- Pipeline **log-based detection**: vuln-web generate log → SOC consume log (model SIEM).
- Vuln-web tidak perlu akses PostgreSQL SOC; enforcement via JSON/API saja.

**File:** `vuln-web/` vs `backend/` vs `frontend/`

---

### Q3. Jelaskan service Docker Compose dan hubungannya.

**Jawaban:**

| Service | Container | Fungsi |
|---------|-----------|--------|
| `postgres` | incidentra_postgres | PostgreSQL — incidents, users, rules |
| `redis` | incidentra_redis | Counter, flags, Celery broker |
| `vuln_web` | incidentra_vulnweb | Target lab — port 5050 |
| `backend` | incidentra_backend | Flask API + Gunicorn — port 5000 |
| `celery_worker` | incidentra_celery | Worker + Beat (cleanup hourly) |
| `frontend` | incidentra_frontend | React — port 3000 |

**Plus:** log monitor = subprocess `docker_log_monitor.py` di dalam backend (`backend/docker_entrypoint.sh`).

**Shared volume `vuln_logs`:** mount ke vuln-web `/app/logs` dan backend `/app/watched_logs` — file sama (`access.log`, `blocked_ips.json`, `rate_limited.json`).

**Kode:**

```48:67:docker-compose.yml
  vuln_web:
    ...
    volumes:
      - vuln_logs:/app/logs
```

```70:104:docker-compose.yml
  backend:
    ...
    volumes:
      - vuln_logs:/app/watched_logs
```

```106:115:docker-compose.yml
  celery_worker:
    command: >
      sh -c "celery -A celery_worker.celery worker ... &
             celery -A celery_worker.celery beat ... &
             wait"
```

---

## B. Vuln-web

### Q4. Urutan hook Flask di `app.py` untuk setiap HTTP request?

**Jawaban:** `before_request` → route handler (`routes/*.py`) → `after_request`.

**File:** `vuln-web/app.py`, `vuln-web/routes/__init__.py`

```26:37:vuln-web/app.py
    @app.before_request
    def _enforce():
        return enforce_security()

    @app.after_request
    def _log(response):
        return log_request(response)
```

```54:56:vuln-web/app.py
    register_blueprints(app)
    return app
```

---

### Q5. Kenapa perlu suffix `POST_DATA:` di access log?

**Jawaban:** Access log Nginx standar **tidak** mencatat body HTTP POST. Brute force login, SQLi POST, file upload butuh body di log agar backend regex/`BruteForceTracker` bisa membaca payload.

**File:** `vuln-web/middleware/logging.py`, `backend/app/core/log_parser.py`

```28:29:backend/app/core/log_parser.py
POST_DATA_PATTERN = re.compile(r'\s+POST_DATA:(.+)$')
```

```33:47:vuln-web/middleware/logging.py
    post_data = ''
    if request.method == 'POST':
        ...
            post_data = ' POST_DATA:' + '&'.join(parts)
```

---

### Q6. Beda GET attack vs POST attack dalam logging?

**Jawaban:**

- **GET:** payload di query string → sudah tercatat di `request.full_path` / `path` log.
- **POST:** payload di body → perlu suffix `POST_DATA:`; `log_parser` merge ke field `query`.

**File:** `vuln-web/middleware/logging.py` (langkah 3), `backend/app/core/log_parser.py`

---

### Q7. Bagaimana vuln-web enforce IP block tanpa PostgreSQL?

**Jawaban:** Baca **`blocked_ips.json`** (Docker shared volume) atau fetch **`GET /api/internal/blocklist`** (Railway). Backend menulis JSON via `response_manager._write_blocked_ips_json()`. Match IP → HTML 403.

**File:** `vuln-web/middleware/security.py`, `backend/app/core/response_manager.py`, `backend/app/api/internal.py`

```117:118:vuln-web/middleware/security.py
    if ip in blocked_data.get('blocked', []):
        return render_template_string(FORBIDDEN_HTML, ip=ip), 403
```

---

### Q8. Apakah ada Redis di vuln-web? Rate limit 429 dihitung bagaimana?

**Jawaban:** **Tidak ada Redis** di vuln-web (`vuln-web/requirements.txt` cuma flask, dotenv, requests).

- Daftar rate-limited: JSON/API (sama seperti block).
- Counting 429: **`_request_log`** dict in-memory — sliding window lokal di process vuln-web.

**File:** `vuln-web/middleware/security.py`

```151:154:vuln-web/middleware/security.py
        now = time.time()
        _request_log[ip] = [t for t in _request_log[ip] if now - t < window]
        _request_log[ip].append(now)
        if len(_request_log[ip]) > max_req:
```

---

### Q9. Fungsi `get_client_ip()` dan prioritas header?

**Jawaban:** `X-Real-IP` → `X-Forwarded-For` (elemen **pertama** = client asli) → `remote_addr` (Docker lokal).

**File:** `vuln-web/ip_utils.py`

```14:27:vuln-web/ip_utils.py
    real_ip = request.headers.get('X-Real-IP')
    ...
    xff = request.headers.get('X-Forwarded-For')
    ...
        first = xff.split(',')[0].strip()
    ...
    return request.remote_addr or 'unknown'
```

---

### Q10. Apa `_fetch_blocklist_remote()` dan kapan dipakai?

**Jawaban:** Fetch blocklist HTTP ke backend saat **`BLOCKLIST_API_URL`** set (Railway / service terpisah). Cache ~3 detik. Docker baca file langsung — fungsi ini tidak dipanggil.

**File:** `vuln-web/middleware/security.py`, `vuln-web/config.py`, `backend/app/api/internal.py`

```109:115:vuln-web/middleware/security.py
    if BLOCKLIST_API_URL:
        combined = _fetch_blocklist_remote()
        ...
    else:
        blocked_data = _load_json_file(BLOCKED_IPS_FILE)
```

```77:99:backend/app/api/internal.py
@internal_bp.route('/blocklist', methods=['GET'])
def get_blocklist():
    ...
    return jsonify({
        'blocked': active_ips,
        'rate_limited': rate_data.get('rate_limited', []),
        'limits': rate_data.get('limits', {}),
```

---

## C. Backend pipeline deteksi

### Q11. Beda `log_parser.py` vs `log_monitor.py`?

**Jawaban:**

| File | Peran |
|------|-------|
| `log_parser.py` | Parse 1 baris string → dict; `LogTailer` baca file |
| `log_monitor.py` | Orkestrator: tail loop, `_process_log_line`, incident, respond |

**Direktori:** `backend/app/core/`

---

### Q12. Apa `LogTailer` dan kenapa tail bukan baca ulang seluruh file?

**Jawaban:** Generator baca baris **baru** dari EOF; saat restart `seek(0,2)` skip log lama → hindari re-process / duplikat massal.

**File:** `backend/app/core/log_parser.py`

```55:61:backend/app/core/log_parser.py
    def tail(self) -> Generator[str, None, None]:
        ...
                f.seek(0, 2)                      # loncat ke EOF — skip log lama
                self._pos = f.tell()
```

---

### Q13. Langkah-langkah `analyze()`?

**Jawaban:**

1. Refresh settings + reload rules (`rules_dirty` / interval)
2. Whitelist check (`BlockedIP.is_whitelist`)
3. Gabung `searchable` string → loop regex per `attack_type`
4. Brute force: POST login path + status 200/401/403 + `BruteForceTracker`
5. Return threat dengan score tertinggi atau `None`

**File:** `backend/app/core/detection_engine.py`

```363:417:backend/app/core/detection_engine.py
    def analyze(self, log_entry: dict) -> Optional[dict]:
        self._refresh_runtime_settings()
        self._maybe_reload_rules()
        ...
        if BlockedIP.query.filter_by(ip_address=ip, is_whitelist=True).first():
            return None
        ...
        for attack_type, patterns in compiled.items():
            ...
                match = pattern.search(searchable)
```

---

### Q14. Apa sliding window di brute force?

**Jawaban:** Hanya hitung attempt POST login dalam **N detik terakhir** (Redis sorted set atau deque lokal). Attempt lama keluar hitungan. Threshold (default 10) → trigger `BRUTE_FORCE`.

**File:** `backend/app/core/detection_engine.py` → class `BruteForceTracker`  
**Env:** `BRUTE_FORCE_THRESHOLD`, `RATE_LIMIT_WINDOW` di `docker-compose.yml`

---

### Q15. Apa dedup incident?

**Jawaban:** IP + `attack_type` sama dalam **5 menit** → tidak INSERT incident baru. Waiver Redis 1× setelah admin unblock (demo).

**File:** `backend/app/core/log_monitor.py`

```150:159:backend/app/core/log_monitor.py
    if not skip_dedup:
        dedup_window = datetime.utcnow() - timedelta(minutes=5)
        recent = Incident.query.filter(
            Incident.source_ip == threat['ip'],
            Incident.attack_type == threat['attack_type'],
            Incident.created_at >= dedup_window,
        ).first()
        if recent:
            return None
```

---

### Q16. Deteksi regex vs brute force?

**Jawaban:**

| | Regex | Brute force |
|--|-------|-------------|
| Input | Pola di path/query/UA/POST_DATA | Counter POST ke path login |
| Engine | Loop `compiled` patterns | `BruteForceTracker.record_attempt()` |
| Contoh | SQLi `' OR 1=1` | 10× POST `/login` dalam 60s |

**File:** `backend/app/core/detection_engine.py` Step 5 vs Step 6

---

## D. Response & Redis

### Q17. Dual-write saat block IP?

**Jawaban:**

1. **PostgreSQL** `BlockedIP` — source of truth UI
2. **`blocked_ips.json`** — vuln-web enforcement
3. **Redis** `blocked:{ip}` — fast flag + TTL

**File:** `backend/app/core/response_manager.py`

---

### Q18. Apa escalating block?

**Jawaban:** Repeat offense → durasi naik (1h → 24h → 7d). Tier disimpan `escalation_count:{ip}` di Redis (dipertahankan saat unblock).

**File:** `backend/app/core/response_manager.py` → `_escalating_block()`

---

### Q19. Sebutkan 5 Redis key penting?

**Jawaban (lihat Appendix A lengkap):**

| Key | Fungsi |
|-----|--------|
| `bf:{ip}:{path}` | Brute force counter |
| `blocked:{ip}` | Fast block flag |
| `ratelimit:{ip}` | Rate limit TTL |
| `escalation_count:{ip}` | Offense tier |
| `rules_dirty` | Signal reload rules dari DB |

**File:** `docs/PEMAHAMAN_PROGRESSIF.md` → Appendix A

---

### Q20. Kenapa AbuseIPDB pakai thread, bukan Celery?

**Jawaban:** Enrichment opsional, HTTP lambat (~1–10s). Thread daemon fire-and-forget — log monitor tidak block. Celery overkill; di project runtime cuma cleanup hourly.

**File:** `backend/app/core/log_monitor.py`

```196:209:backend/app/core/log_monitor.py
    from app.services.threat_intel_service import _do_reputation_check
    ...
            threading.Thread(
                target=_rep_thread,
                args=(app, incident.id, threat['ip']),
                daemon=True,
```

**File enrichment:** `backend/app/services/threat_intel_service.py`

---

## E. Sync vs Thread vs Celery

### Q21. Beda sync, thread, Celery — 1 contoh masing-masing?

**Jawaban:**

| Pola | Contoh | File |
|------|--------|------|
| **Sync** | Explain AI, `analyze()` per baris | `incidents.py`, `detection_engine.py` |
| **Thread** | AbuseIPDB, email alert | `log_monitor.py`, `response_manager.py` |
| **Celery** | `cleanup_expired_blocks` hourly | `backend/celery_worker.py` |

**Doc:** `docs/PEMAHAMAN_PROGRESSIF.md` → §16

---

### Q22. Task Celery terdaftar vs yang benar-benar jalan?

**Jawaban:**

**Terdaftar** (import di `celery_worker.py` baris 8–10):

- `cleanup_expired_blocks` ✅ **jalan** (Beat hourly)
- `generate_explanation_task` ❌ explain = sync HTTP
- `notify_critical_incident` ❌ email = thread
- `check_ip_reputation` ❌ AbuseIPDB = thread

**File:** `backend/celery_worker.py`

```13:14:backend/celery_worker.py
@celery.task
def cleanup_expired_blocks():
```

```94:98:backend/celery_worker.py
celery.conf.beat_schedule = {
    'cleanup-expired-blocks-hourly': {
        'task': 'celery_worker.cleanup_expired_blocks',
        'schedule': 3600.0,
```

---

### Q23. Apa yang dilakukan `cleanup_expired_blocks`?

**Jawaban:**

1. DELETE `BlockedIP` temporary yang `expire_time < now`
2. `_write_blocked_ips_json()` sync file
3. Bersihkan `rate_limited.json` — hapus IP expired + delete `ratelimit:{ip}` Redis

**File:** `backend/celery_worker.py` baris 21–77

---

## F. Frontend & API

### Q24. Bagaimana frontend akses REST API?

**Jawaban:** `frontend/src/services/api.js` — axios + `baseURL`. Login → JWT `localStorage`. Interceptor tempel `Authorization: Bearer`. Halaman import fungsi (`getDashboardStats`, dll.).

```12:24:frontend/src/services/api.js
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';
const api = axios.create({ baseURL: API_URL, ... });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('incidentra_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
```

**Blueprint register:** `backend/app/__init__.py`

---

### Q25. Kenapa URL API langsung di browser dapat `Authorization required`?

**Jawaban:** Address bar tidak kirim header JWT. Axios dari React otomatis attach token dari `localStorage`.

**File:** `backend/app/api/auth_middleware.py`

```16:18:backend/app/api/auth_middleware.py
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401
```

---

### Q26. Alur chart "By Severity"?

**Jawaban:**

1. `Dashboard.js` → `fetchStats()` → `getDashboardStats()`
2. `dashboard.py` → `severity_breakdown` JSON
3. `setStats(res.data)` → map ke Chart.js → `<Doughnut data={severityData}>`

**File:** `frontend/src/pages/Dashboard.js`, `backend/app/api/dashboard.py` baris 77–80, 149

---

### Q27. Globe Attack Origins — dari mana data? Kenapa bukan Chart.js?

**Jawaban:**

- `country_code` dari AbuseIPDB thread → PostgreSQL → API `top_countries`
- Frontend `AttackOriginsGlobe.js` → `getCountryCentroid(code)` → `react-globe.gl`
- Butuh koordinat 3D — bukan chart 2D

**File:** `frontend/src/components/dashboard/AttackOriginsGlobe.js`, `frontend/src/data/countryCentroids.js`, `backend/app/api/dashboard.py` baris 109–119

---

## G. Auth & RBAC

### Q28. Alur login JWT?

**Jawaban:** `Login.js` → `api.login()` → `auth.py` POST `/login` → JWT → `App.js` `localStorage` → interceptor setiap request → `verify_token()` per blueprint.

**File:** `frontend/src/pages/Login.js`, `backend/app/api/auth.py`, `frontend/src/App.js`

---

### Q29. Admin vs analyst — contoh admin-only?

**Jawaban:** Simulate / inject-log / detection test → `@require_role('admin')`.

**File:** `backend/app/api/detection.py`

```119:121:backend/app/api/detection.py
@detection_bp.route('/simulate', methods=['POST'])
@require_role('admin')
def simulate_attack():
```

**UI:** `frontend/src/pages/Incidents.js`, `frontend/src/pages/DetectionRules.js` — wrap `isAdmin`

---

### Q30. Kenapa simulate hanya admin?

**Jawaban:** Bisa trigger incident + block sungguhan — risiko abuse di environment demo/shared.

---

## H. Pertanyaan jebakan

### Q31. Redis mati — apa yang masih jalan?

**Jawaban:**

- **Masih:** API UI, PostgreSQL, deteksi regex (partial), JSON enforcement vuln-web (jika file sudah ditulis)
- **Rusak/lemah:** Brute force counter Redis, Celery broker/beat, fast flags, heartbeat Redis, rules_dirty signal

---

### Q32. Log monitor mati — dampak UI?

**Jawaban:** Banner stale Dashboard (`GET /dashboard/log-status`, >60s). Tidak ada incident baru otomatis. API/UI tetap jalan.

**File:** `backend/app/api/dashboard.py` → `log-status`, `frontend/src/pages/Dashboard.js`

---

### Q33. Kenapa deteksi tidak peduli HTTP 200 vs 403?

**Jawaban:** **Signature-based** — pola serangan di log, bukan “exploit sukses”. Model WAF/SIEM umum: attempt tetap dicatat.

**Exception:** Brute force hanya count status 200/401/403 pada path login.

---

### Q34. IP private — kenapa globe kosong?

**Jawaban:** AbuseIPDB skip non-public IP → `country_code` null → `top_countries` kosong.

**File:** `backend/app/services/threat_intel_service.py` baris 17–22

---

### Q35. Kelemahan arsitektur capstone?

**Jawaban (jujur):**

- Vuln-web `_request_log` reset saat restart container
- Blocklist fetch Railway fail-open jika backend down
- Explain AI sync blocking (5–30s)
- Single-node demo, bukan high-availability production

---

## I. Demo live (checklist)

### Q36. Demo SQLi GET

**Langkah:** Attack URL di vuln-web → lihat baris di `access.log` → incident di UI → (opsional) block.

**File trace:** `vuln-web/routes/` → `logging.py` → `log_monitor.py` → `detection_engine.py`

---

### Q37. Demo brute force login

**Langkah:** 10× POST login dalam 60s → jelaskan sliding window + threshold.

**Env:** `BRUTE_FORCE_THRESHOLD=10` di `docker-compose.yml` baris 89

---

### Q38. Demo unblock IP

**Langkah:** DELETE blocked IP → DB row hapus → JSON sync → Redis waiver → vuln-web boleh akses lagi.

**File:** `backend/app/api/blocked_ips.py`, `response_manager.py`

---

### Q39. Network tab — Authorization header

**Langkah:** F12 → Network → request `stats` → Headers → `Authorization: Bearer ...`

**File:** `frontend/src/services/api.js`

---

### Q40. Before/after block di vuln-web

**Langkah:** IP blocked → refresh vuln-web → halaman 403 HTML dari `FORBIDDEN_HTML`.

**File:** `vuln-web/middleware/security.py` baris 33–41, 117–118

---

## Cheat sheet 1 halaman (hafal pola)

```
LOG:    vuln-web/middleware/logging.py → access.log
TAIL:   backend/app/core/log_parser.py → LogTailer
PARSE:  backend/app/core/log_parser.py → parse_log_line
DETECT: backend/app/core/detection_engine.py → analyze()
ACT:    backend/app/core/log_monitor.py → _process_log_line
BLOCK:  backend/app/core/response_manager.py → respond()
ENFORCE:vuln-web/middleware/security.py → enforce_security()
UI:     frontend/src/services/api.js → backend/app/api/*.py

Redis:  backend only (bukan vuln-web)
Celery: cleanup_expired_blocks hourly only
Thread: AbuseIPDB + email
Sync:   analyze, Explain AI, login
```

---

## Index direktori penting

```
incidentra/
├── docker-compose.yml          # 6 service + volume vuln_logs
├── vuln-web/
│   ├── app.py                  # before/after_request hooks
│   ├── ip_utils.py             # get_client_ip
│   ├── middleware/
│   │   ├── logging.py          # POST_DATA + access.log
│   │   └── security.py         # 403/429 enforcement
│   └── routes/                 # handler lab (bukan di app.py)
├── backend/
│   ├── celery_worker.py        # Celery cleanup
│   ├── docker_log_monitor.py   # start_monitor entry
│   └── app/
│       ├── core/
│       │   ├── log_parser.py
│       │   ├── log_monitor.py
│       │   ├── detection_engine.py
│       │   └── response_manager.py
│       ├── api/
│       │   ├── auth.py / auth_middleware.py
│       │   ├── dashboard.py
│       │   ├── detection.py
│       │   └── internal.py     # Railway ingest + blocklist
│       └── services/
│           └── threat_intel_service.py  # AbuseIPDB
└── frontend/
    └── src/
        ├── services/api.js
        └── pages/Dashboard.js
```

---

*Terakhir diupdate: sesi latihan sidang — companion `PEMAHAMAN_PROGRESSIF.md`.*
