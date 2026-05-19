# SME-Guard — Aplikasi & Arsitektur

**SME-Guard** adalah platform Web-SOC untuk UKM: memantau log aplikasi web, mendeteksi serangan (SQLi, XSS, brute force, path traversal, dll.), membuat insiden, memblokir IP otomatis, dan menampilkan dashboard analis keamanan.

> Capstone — President University, Faculty of Computer Science  
> Repo: [github.com/HardInCode/sme-guard](https://github.com/HardInCode/sme-guard)

**Menjalankan sistem:** [TUTORIAL.md](TUTORIAL.md) · **Clone & push:** [GITHUB.md](GITHUB.md) · **Checklist uji:** [AUDIT_2026-05-19.md](AUDIT_2026-05-19.md)

---

## Ringkasan kemampuan

| Area | Kemampuan |
|------|-----------|
| Monitoring | Tail `access.log` atau mode simulasi demo |
| Deteksi | Regex + aturan DB + threshold brute force (Redis) |
| Respons | Monitor / rate limit / blokir temp / blokir permanen |
| SOC UI | Dashboard, insiden (ongoing vs arsip), **IP Management**, rules, live traffic |
| AI | Penjelasan insiden & chatbot (Groq, opsional) |
| Intel | AbuseIPDB (opsional), notifikasi email/Telegram |
| Akses | JWT, peran admin & analyst, i18n EN/ID, dark theme |
| Deploy | Docker Compose (laptop/VPS) — [DEPLOY.md](DEPLOY.md) |

---

## Docker vs manual

| | Docker | Manual |
|---|--------|--------|
| Clone | `git clone` → `copy .env.docker.example .env.docker` | `copy .env.example .env` |
| Env backend | `.env.docker` (secrets) + `docker-compose.yml` (DB/Redis URL) | `backend/.env` |
| DB driver | `postgresql+psycopg://...@postgres:5432/...` | `postgresql+psycopg://...@localhost:5432/...` |
| Log & JSON | Volume `vuln_logs` → `/app/watched_logs` = `/app/logs` | `../vuln-web/logs/` |
| Log monitor | `docker_log_monitor.py` + gunicorn | `python run.py` |
| Frontend API | Build arg `REACT_APP_API_URL` | `package.json` proxy atau `.env` |

---

## Arsitektur sistem

```mermaid
flowchart LR
  subgraph client [Klien / Penyerang]
    B[Browser / curl]
  end
  subgraph target [Target]
    V[vuln-web :5050]
    L[access.log]
    J[blocked_ips.json / rate_limited.json]
  end
  subgraph soc [SME-Guard]
    F[Frontend React :3000]
    API[Flask API :5000]
    LM[Log Monitor]
    DE[Detection Engine]
    RM[Response Manager]
  end
  subgraph data [Data]
    PG[(PostgreSQL)]
    R[(Redis)]
  end
  B --> V
  V --> L
  LM --> L
  LM --> DE
  DE --> API
  DE --> RM
  RM --> PG
  RM --> J
  RM --> R
  J --> V
  F --> API
  API --> PG
  API --> R
```

### Alur satu baris log

1. **vuln-web** mencatat HTTP ke `access.log` (format combined + `POST_DATA` untuk login).
2. **LogTailer** membaca baris baru.
3. **parse_log_line** → `{ ip, method, path, query, user_agent, status_code }`.
4. **DetectionEngine.analyze** → pola / brute force / scanner UA (tie-break PATH_TRAVERSAL vs LFI_RFI untuk `?file=../../` tanpa `php://`).
5. Ancaman → **Incident** di PostgreSQL + **ResponseManager.respond**.
6. ResponseManager → **BlockedIP** (DB) + **`blocked_ips.json`** / **`rate_limited.json`** + Redis.
7. **vuln-web** `before_request` baca JSON → **403** atau **429**.
8. Opsional: AI explanation, AbuseIPDB, notifikasi.

Dedup: IP + attack_type dalam 5 menit. Setelah unblock: waiver Redis + clear rate limit + reset brute-force counter.

---

## Data & penyimpanan (PostgreSQL vs JSON vs Redis)

| Store | Isi | Mengapa tidak semua di DB? |
|-------|-----|----------------------------|
| **PostgreSQL** | users, incidents, incident_logs, explanations, notes, **blocked_ips**, detection_rules, app_settings, audit_logs | Rekaman SOC, query, laporan, relasi |
| **Redis** | brute-force counter, `ratelimit:{ip}`, `blocked:{ip}`, waiver unblock, `rules_dirty` | State cepat & TTL; bukan arsip jangka panjang |
| **access.log** | Traffic mentah vuln-web | Volume besar; sumber deteksi real-time |
| **blocked_ips.json** | Daftar IP yang harus 403 di vuln-web | vuln-web **tidak** connect ke PostgreSQL |
| **rate_limited.json** | Daftar IP rate limit + `limits.{ip}` (max req, window) | Enforcement 429 di vuln-web; disinkron dari UI |

### Dual-write Blocked IP

- **DB** = sumber untuk UI (reason, expire, edit, audit, incident_count).
- **JSON** = kontrak ke vuln-web (tanpa restart saat unblock).

### Rate limit — sengaja tanpa tabel DB

Sesuai desain sejak Bab 3 capstone: rate limit adalah **kebijakan enforcement sementara**, bukan entitas bisnis seperti insiden. Penyimpanan:

- **JSON** — vuln-web baca per request.
- **Redis** — TTL penegakan backend.
- **UI** — tab **Rate Limited** di IP Management (`GET/PATCH/DELETE /api/rate-limited/`).

Unblock IP di tab Blocked juga menghapus entry rate limit.

### Keselarasan Form 2/3 (ERD & diagram alur)

Diagram capstone Anda sudah benar secara konsep:

| Komponen Form 2 | Implementasi kode |
|-----------------|-------------------|
| `blocked_ips` di ERD | Tabel PostgreSQL + salinan `blocked_ips.json` |
| Rate limit di diagram JSON | `rate_limited.json` + Redis (tanpa tabel terpisah) |
| `incident_logs.action_taken` | Mencatat "rate limiting applied" / blokir — bukan menggantikan tabel rate limit |

**Mengapa blocked IP di DB tetapi rate limit tidak?**

- **Blocked IP (high/critical):** butuh metadata SOC (alasan, expire, edit dari UI, jumlah insiden, audit). Itu cocok di relational DB.
- **Rate limit (medium):** sifatnya **sementara**; Form 2 menempatkan enforcement di JSON agar vuln-web baca tanpa koneksi DB. Histori ada lewat `incident` + `incident_logs`, bukan tabel `rate_limited_ips`.

**Keduanya tetap pakai JSON** untuk vuln-web — blocked IP **juga** ditulis ke `blocked_ips.json` setelah disimpan di DB (dual-write).

### Keamanan JSON — apakah bisa dibypass?

**Ya, jika penyerang punya akses tulis ke folder log di server yang sama** dengan vuln-web (mis. shell di container/host). Mereka bisa mengedit `blocked_ips.json` / `rate_limited.json` dan menghapus IP mereka.

Untuk **capstone lab** ini dapat diterima dengan asumsi:

- Penyerang hanya mengirim HTTP, tidak punya SSH/RCE ke server SOC.
- File JSON di volume bersama dengan permission terbatas.

Mitigasi produksi (sebut di Bab 4 sebagai *future work*): permission file ketat, WAF di depan app, enforcement di reverse proxy, atau vuln-web baca policy dari API internal — bukan file world-writable.

Grafik Dashboard memakai **`Incident.created_at`** — bukan isi log. Demo grafik: `scripts/seed_chart_demo.py`.

Skema DB dibuat dengan `db.create_all()` (bukan migrasi Alembic terpisah). Lihat [LEARNING.md §6](LEARNING.md#6-database-json-dan-bab-capstone).

---

## Komponen repositori

```
sme-guard/
├── backend/           Flask API, detection, response_manager
├── frontend/          React 18 + MUI
├── vuln-web/          Target lab + enforcement JSON
├── scripts/           reset, seed, init SQL
├── docs/              Dokumentasi
├── docker-compose.yml
└── README.md
```

### Backend (`backend/app/`)

| Modul | Peran |
|-------|--------|
| `core/log_parser.py` | Parse log, LogTailer, SimulatedLogFeeder |
| `core/log_monitor.py` | Pipeline deteksi |
| `core/detection_engine.py` | Pola OWASP + brute force |
| `core/response_manager.py` | Severity → aksi + sinkron JSON |
| `api/incidents.py` | CRUD, bulk, export CSV |
| `api/blocked_ips.py` | Blokir + sync JSON |
| `api/rate_limited.py` | Kelola rate limit (JSON/Redis) |
| `api/dashboard.py` | Stats, timeline |
| `api/rules.py`, `traffic.py`, `auth.py`, `settings.py`, `audit.py` | SOC standar |

Entry: `run.py` (manual) · `docker_entrypoint.sh` + gunicorn (Docker).

### Frontend

| Halaman | Route | Catatan |
|---------|-------|---------|
| Dashboard | `/` | Timeline, MTTR |
| Incidents | `/incidents` | Ongoing |
| All Incidents | `/incidents/all` | Arsip |
| Incident Detail | `/incidents/:id` | AI, catatan |
| **IP Management** | `/blocked-ips` | Tab **Blocked** \| **Rate Limited** |
| Rules | `/rules` | |
| Live Traffic | `/traffic` | Dari log file |
| Settings | `/settings` | |
| Audit Log | `/audit` | Admin |

### Vuln-web

Target rentan + middleware JSON (403/429). Per-IP rate policy dari `limits` di `rate_limited.json`.

---

## Model respons keamanan

| Level | Severity | Tindakan |
|-------|----------|----------|
| 1 | low | Log & monitor |
| 2 | medium | Rate limit (JSON + Redis) |
| 3 | high | Blokir sementara (`TEMP_BLOCK_DURATION`, default 86400 s) |
| 4 | critical | Blokir permanen + notifikasi |

Env: `BRUTE_FORCE_THRESHOLD`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW` — global; override per IP lewat UI Rate Limited.

---

## API utama (`/api`)

Auth: `Authorization: Bearer <token>` kecuali login.

### Insiden

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| GET | `/incidents/` | Filter, sort, page |
| PUT | `/incidents/<id>/status` | Ubah status |
| PATCH | `/incidents/bulk-status` | Admin bulk resolve |
| GET | `/incidents/export` | CSV |

### IP Management

| Method | Endpoint | Keterangan |
|--------|----------|------------|
| GET/POST/PATCH/DELETE | `/blocked-ips/` | Blokir (DB + JSON) |
| GET | `/rate-limited/` | Daftar rate limit + TTL |
| PATCH | `/rate-limited/<ip>` | Extend TTL, max_requests, window |
| DELETE | `/rate-limited/<ip>` | Clear rate limit |

### Lainnya

`GET /dashboard/stats` · `GET/PUT /rules` · `GET /traffic/recent` · `POST /detection/simulate` · `GET/PUT /settings` · `GET /audit` · `POST /chatbot`

---

## Peran pengguna

| Fitur | Admin | Analyst |
|-------|:-----:|:-------:|
| Dashboard & insiden | ✓ | ✓ |
| Bulk resolve | ✓ | ✗ |
| IP Management (block / rate limit) | ✓ | lihat saja |
| Rules / settings | ✓ | terbatas |
| Audit log | ✓ | ✗ |

---

## Integrasi opsional

| Layanan | Env | Jika kosong |
|---------|-----|-------------|
| Groq | `GROQ_API_KEY` di `.env` / `.env.docker` | Fallback penjelasan |
| AbuseIPDB | Settings / env | Skip reputasi IP |
| SMTP / Telegram | env / Settings | Tanpa alert |

Celery ada; notifikasi/AI punya fallback thread jika worker tidak jalan.

---

## Mode log monitor

| `USE_SIMULATED_LOGS` | `DEMO_MODE` | Perilaku |
|----------------------|-------------|----------|
| `true` | `true` | Feeder sekali |
| `true` | `false` | Feeder berulang |
| `false` | — | Tail log nyata |

---

## Status pengembangan (Mei 2026)

| Fitur | Status |
|-------|--------|
| Edit durasi blokir (UI) | ✅ |
| IP Management + rate limit UI | ✅ |
| Per-IP max requests / window | ✅ (JSON `limits`) |
| Docker Compose end-to-end | ✅ |
| Notification bell in-app | 🔲 opsional |
| Pengelompokan insiden (correlation) | 🔲 opsional Bab 4+ |

---

## Tim

| Nama | NIM | Peran |
|------|-----|-------|
| Hardin Irfan | 001202300066 | Project Lead & Backend |
| Nasywa Kamila | 001202300211 | AI Engineer & Frontend |
| Zaidan Mahfudz Azzam Saidi | 001202300144 | Security & QA |
