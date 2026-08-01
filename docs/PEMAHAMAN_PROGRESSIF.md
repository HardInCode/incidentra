# PEMAHAMAN INCIDENTRA — HULU KE HILIR FILE BY FILE

> **Cara pakai file ini** (baca ini dulu sebelum isi apapun):
> 1. Jalankan aplikasinya (`docker compose up`), buka browser.
> 2. Pilih satu section di bawah (mulai dari #1 — Login & Register). Klik-klik fitur itu di UI.
> 3. Buka file-file yang tercantum di tabel "Files terlibat", tekan **Ctrl+F**, cari kata di kolom "Anchor" — itu langsung lompat ke fungsi intinya. Baca sekilas.
> 4. Isi bagian **"Pemahaman saya"** dengan bahasamu sendiri — sepotong-sepotong juga tidak masalah, ini draft internal, bukan laporan resmi.
> 5. Tulis pertanyaan spesifik di **"Pertanyaan saya"**, dinomori (Q1, Q2, ...). Makin spesifik makin cepat & akurat dijawab — sebut nama fungsi/file kalau tahu.
> 6. Kirim section itu ke saya (paste atau `@` file ini + nomor section). Saya isi **"Jawaban"** dengan referensi baris kode asli, tidak akan menjawab dari ingatan/asumsi.
> 7. Setelah satu section beres dan kamu paham, lanjut ke section berikutnya. Tidak perlu urut kalau ada yang lebih penasaran duluan.
>
> **Kenapa formatnya begini:** supaya kamu yang mengarahkan (kamu yang tahu bagian mana yang masih buram), saya cuma menjawab presisi — bukan saya yang mendikte alur pemahamanmu.

**Status pengerjaan** (update manual, centang kalau section sudah "klik" di kepala):

- [x] 1. Login & Self-Registration
- [~] 2. Dashboard — flow + CHART 1 OK; widget lain cukup "Dashboard lite" (lihat Section 2)
- [ ] 3. Log Ingestion → Detection (dari access.log sampai jadi Incident)
- [ ] 4. Automated Response (block/rate-limit/escalation)
- [ ] 5. Incident Detail + AI Explanation (Groq)
- [ ] 6. IP Management (Blocked/Rate Limited/Whitelist)
- [ ] 7. Detection Rules CRUD + rules_dirty reload
- [ ] 8. Notifications (Email/Telegram) + AbuseIPDB
- [ ] 9. Settings + User Management (RBAC) + Audit Log
- [ ] 10. Docker Compose — bagaimana 6 service saling terhubung

---

## Pemahaman base utama (boot frontend)

1. Browser pertama kali muat `frontend/public/index.html` — halaman HTML kosong + `<div id="root">`.
2. `frontend/src/index.js` mount React: `ReactDOM.createRoot(...).render(<App />)`.
3. `frontend/src/App.js` memutuskan auth + routing: belum login → `/login` (Login.js); sudah login → `/` + halaman lain di dalam `Layout`.
4. `frontend/src/components/shared/Layout.js` = sidebar/navbar + area konten (`{children}`). **Bukan** di App.js — App.js hanya routing table.

## 1. Login & Self-Registration

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Frontend | `frontend/public/index.html` | `#root` |
| Frontend | `frontend/src/index.js` | `createRoot`, `<App />` |
| Frontend | `frontend/src/App.js` | `handleLogin`, `isAuthenticated`, `Navigate` |
| Frontend | `frontend/src/pages/Login.js` | `Ctrl+F` (baris 1) → `handleLogin`, `handleRegister` |
| Frontend | `frontend/src/services/api.js` | `login`, `register` |
| Backend | `backend/app/api/auth.py` | `Ctrl+F` (baris 1) → `login`, `register`, `_make_token`, `_register_rate_limited` |
| Backend | `backend/app/api/auth_middleware.py` | `verify_token` |
| Backend | `backend/app/models/__init__.py` | `class User` |

**Alur (isi sendiri sambil klik-klik):**

 
1. klik login menggunakan admin credentials yang sudah di seed, berhasil masuk
2. klik login menggunakan username yang tidak terdaftar, tidak berhasil masuk 
3. register harus menggunakan 2 persyaratan password, sama dengan confirmation field & 8 char length
4. saat berhasil registrasi harus approval admin terlebih dahulu.


**Pemahaman saya:**

1. Login memanggil function handleLogin untuk mengirim request `POST` login ke backend melalui `api.js`, Register melakukan hal yang mirip dengan login, yaitu melalu perantara file `api.js` dia mengirim request ke backend untuk registrasi menggunakan function handleRegister.
2. File `api.js` menggunakan library axios untuk melakukan proses request atau pemanggilan ke backend url yang bisa diset file ENV Frontend dengan fallback URL yang bisa di set di file api.js langsung.
3. Endpoint restAPI yang berupa URL prefix sebagai blueprint yang berasal dari `backend/app/__init__.py` file tersebut mengimport setiap file blueprint di dalam folder `backend/app/api` lalu melakukan `register_blueprint`, tidak semua file di dalam `backend/app/api` adalah blueprint, ada sebagian cuma helper.
4. route `/login` berasal dari file `auth.py` yaitu `@auth_bp.route('/login', methods=['POST'])` lalu frontend mengirim POST request dengan payload json username dan password melalui `api.js`.
5. route `/register` persis dengan route `/login`, dari `@auth_bp.route('/register', methods=['POST'])` dan frontend memanggilnya melalui `api.js` untuk mengirim POST request daftar payload username, email, & password (confirmPassword hanya divalidasi di frontend). Setelah berhasil daftar user otomatis `status=pending`, `role=None` — terdaftar di database sebelum admin assign role di User Management.
6. Terdapat perlindungan anti spam register: `_register_rate_limited()` di Redis (max 5/jam per IP) — **beda** dari rate limit IP attack di vuln-web (Redis + `rate_limited.json`).
7. File blueprint `auth.py` untuk logic login/register. Selain `/login` dan `/register`, ada `GET /users` (`list_users`) — dipakai `IncidentDetail.js` untuk dropdown assign incident (bukan halaman User Management; itu `GET /api/users/` di `users.py`).
8. Setelah POST login, backend `auth.py` cocokkan username + `check_password_hash` via SQLAlchemy. Jika OK, `_make_token()` generate JWT → response `{ token, user }` → `Login.js` panggil `onLogin(res.data.token)`.
9. `App.js` `handleLogin(token)` simpan ke `localStorage` (`incidentra_token`), set `isAuthenticated=true` → React Router `<Navigate to="/" />` → Dashboard.

kesimpulan:

1. User submit form → handleLogin / handleRegister di Login.js
2. Panggil login() / register() di api.js (axios)
3. Request ke http://localhost:5000/api + path (ENV atau fallback)
4. Flask: blueprint prefix /api/auth (__init__.py) + route /login (auth.py) = /api/auth/login
5. Backend proses → balikin JSON → frontend simpan token / tampilkan pesan

Frontend React memanggil backend Flask lewat axios di api.js. Base URL di-set via environment variable dengan fallback localhost:5000/api. Backend memakai Flask Blueprint — prefix /api/auth diregister di app factory, route /login didefinisikan di auth.py, sehingga endpoint penuh menjadi POST /api/auth/login.

**Pertanyaan saya:**

- Q1. Apakah sudah cukup aman secara keamanan? mengingat web SOC adalah web keamanan pasti akan ditanyai mengenai hal ini, implementasi keamanan web SOC itu sendiri.

**Jawaban:**

- **A1.** Cukup untuk capstone SME dengan catatan berikut:
  - **Password:** disimpan sebagai hash scrypt (Werkzeug `generate_password_hash` / `check_password_hash`), tidak plain text di DB.
  - **Login:** error unified `invalid_credentials` (username salah = password salah) — anti user enumeration.
  - **JWT:** HS256, signed `SECRET_KEY`, expire 24 jam; setiap API call diverifikasi `verify_token()` + cek status user live di DB (pending/suspended ditolak meski token masih ada).
  - **Register:** rate limit Redis 5/jam per IP; password min 8 char; akun pending sampai admin approve + assign role.
  - **Transport:** production wajib HTTPS — payload login terlihat di DevTools browser user sendiri (normal), bukan celah remote.
  - **Keterbatasan scope:** belum 2FA, belum refresh-token rotation — acceptable untuk capstone; bisa disebut sebagai future work di sidang.

---

## 2. Dashboard (KPI cards, charts, globe)

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Frontend | `frontend/src/App.js` | `Dashboard`, `isAuthenticated`, route `/` |
| Frontend | `frontend/src/pages/Dashboard.js` | `fetchStats`, `CHART 1`, `checkLogStatus` |
| Frontend | `frontend/src/services/api.js` | `getDashboardStats`, `getLogStatus` |
| Frontend | `frontend/src/components/dashboard/AttackOriginsGlobe.js` | *(globe — data `top_countries`)* |
| Backend | `backend/app/api/dashboard.py` | `get_stats`, `log_status`, `timeline_raw` |

**Library yang dipakai di Dashboard.js:**

| Library | Fungsi |
|---|---|
| `@mui/material` + `@mui/icons-material` | Layout, Card, Grid, Chip, CircularProgress, dll. |
| `react-chartjs-2` (`Line`, `Doughnut`, `Bar`) | Wrapper React untuk Chart.js |
| `chart.js` | Engine chart (register scale/element di baris register) |
| `react-globe.gl` (via `AttackOriginsGlobe.js`) | Globe 3D attack origins — lazy load |

**Pemetaan section UI → data backend:**

| Section di layar | Field JSON dari `GET /api/dashboard/stats` | Chart / komponen |
|---|---|---|
| Header + refresh | `lastRefresh` (frontend only) | — |
| Warning kuning "No logs in 60s" | `GET /api/dashboard/log-status` → `{ stale: true }` | — |
| System Status banner | `system_status` | `SystemStatusBanner` |
| Total Incidents | `total_incidents` | `StatCard` |
| Last 24 Hours | `last_24h` | `StatCard` |
| Blocked IPs | `blocked_ips` | `StatCard` |
| MTTR | `mttr_minutes` | `StatCard` |
| Incident Timeline (7 days) | `timeline[]` → `{ date, count }` | **CHART 1** — `Line` (`timelineData`) |
| By Severity | `severity_breakdown[]` | **CHART 2** — `Doughnut` (`severityData`) |
| Severity Trend (7 days) | `severity_timeline[]` | **CHART 3** — `Line` multi-series (`severityTrendData`) |
| Attack Origins globe | `top_countries`, `geo_enriched_7d`, `last_7d` | **Globe** — `AttackOriginsGlobe` |
| Attack Types | `attack_breakdown[]` | **CHART 5** — `Bar` (`attackData`) |
| Top Attacking IPs | `top_attacking_ips[]` | list + `LinearProgress` (bukan Chart.js) |

**Alur:**

1. Setelah login, React Router arahkan ke `/` → render `Dashboard.js`
2. `useEffect` panggil `fetchStats()` + `checkLogStatus()` sekali saat mount
3. `fetchStats` → `getDashboardStats()` di `api.js` → `GET http://localhost:5000/api/dashboard/stats` (JWT di header dari interceptor)
4. Backend `dashboard.py` `get_stats()` query PostgreSQL (`incidents`, `blocked_ips`) → return JSON agregat
5. Frontend simpan ke `stats` state → siapkan `timelineData`, `severityData`, dll. → render chart
6. Auto-refresh: stats tiap 15s (`REFRESH_INTERVAL`), log-status tiap 30s
7. Tombol refresh manual memanggil `fetchStats()` lagi

**Pemahaman saya:**

1. Setelah login sukses, route diarahkan ke `/` → render `Dashboard.js`. Di DevTools Network: request `login` (dapat token) lalu `stats` (dengan header `Authorization: Bearer ...`).
2. Saat pertama buka Dashboard (**mount**), `useEffect` jalankan `fetchStats()` + `checkLogStatus()` → data tampil.
3. `fetchStats()` → `getDashboardStats()` di `api.js` → `GET /api/dashboard/stats` → `dashboard.py` `get_stats()`.
4. Response JSON → `setStats(res.data)`. `stats` dari `useState(null)` — setter-nya `setStats`.
5. `checkLogStatus()` poll tiap **30 detik**; backend anggap stale jika tidak ada log **60 detik** (`stale: true` → banner kuning).
6. Angka 0 di UI = DB belum ada incident — bukan error frontend.

**CHART 1 — Incident Timeline (7 Days)** — sudah dipahami hulu→hilir:

- `fetchStats()` → `get_stats()` → query `timeline_raw` (COUNT incident GROUP BY date, 7 hari)
- `_fill_timeline()` isi hari tanpa incident dengan `count: 0`
- JSON field `timeline` → frontend `setStats(res.data)`
- Pisah jadi `timelineCounts` (sumbu Y) + `timelineLabels` (sumbu X, `formatChartDay`)
- Gabung `timelineData` format Chart.js → `<Line data={timelineData} />` (kiri atas, garis cyan)

**Belum dipelajari detail:** CHART 2, 3, 5, Globe, Top IPs list.

**Pertanyaan saya:**

- Q1. (kosong — lanjut belajar chart lain nanti)

**Jawaban:**

- A1. —

---

## 3. Log Ingestion → Detection

> **Status:** kerangka siap — isi "Pemahaman saya" besok sambil demo. Ini **jantung sidang**; Section 4 (response) lanjutan langsung dari sini.

**Files terlibat:**

| Layer | File | Ctrl+F anchor | Peran singkat |
|---|---|---|---|
| Target app | `vuln-web/middleware/logging.py` | `log_request`, `POST_DATA` | Tulis baris log (NCSA + body POST) ke file atau push HTTP |
| Docker | `docker-compose.yml` | `vuln_logs`, `WEB_SERVER_LOG_PATH` | Volume shared: vuln-web tulis, backend tail |
| Backend startup | `backend/docker_entrypoint.sh` | `docker_log_monitor.py` | Monitor jalan terpisah dari Gunicorn (Docker) |
| Backend startup | `backend/run.py` | `start_monitor` | Monitor jalan saat `python run.py` (dev manual) |
| Backend | `backend/docker_log_monitor.py` | `start_monitor` | Process standalone tail log di container |
| Backend | `backend/app/core/log_parser.py` | `parse_log_line`, `LogTailer`, `POST_DATA_PATTERN` | String log → dict `{ ip, method, path, query, ... }` |
| Backend | `backend/app/core/log_monitor.py` | `_process_log_line`, `ingest_log_lines`, `start_monitor` | Orkestrator: parse → detect → incident → response |
| Backend | `backend/app/core/detection_engine.py` | `DETECTION_PATTERNS`, `analyze`, `BruteForceTracker` | Regex + threshold → threat dict atau `None` |
| Backend | `backend/app/models/__init__.py` | `class Incident`, `class DetectionRule` | Row incident + rule match_count |
| Backend (opsional) | `backend/app/api/internal.py` | `ingest_logs` | Hanya deployment terpisah (Railway); Docker pakai shared file |
| Backend (opsional) | `backend/app/api/detection.py` | `inject` | Manual inject log untuk testing |

**Diagram alur (hulu → hilir):**

```mermaid
flowchart LR
  A[User attack vuln-web :5050] --> B[logging.py log_request]
  B --> C[(access.log shared volume)]
  C --> D[LogTailer tail baris baru]
  D --> E[parse_log_line]
  E --> F[DetectionEngine.analyze]
  F -->|threat| G[_process_log_line]
  G --> H[(PostgreSQL incidents)]
  G --> I[response_manager.respond]
  F -->|None| J[abaikan — traffic normal]
```

**Alur langkah demi langkah (isi centang besok):**

1. [ ] Attacker kirim request ke vuln-web (contoh SQLi di query/form)
2. [ ] `logging.py` `log_request()` — setelah response, format baris NCSA Combined Log
3. [ ] Kalau POST: append `POST_DATA:key=val&...` supaya detection bisa baca body (bukan cuma URL)
4. [ ] Docker: tulis ke `/app/logs/access.log` (vuln-web) = `/app/watched_logs/access.log` (backend) via volume `vuln_logs`
5. [ ] `docker_log_monitor.py` → `start_monitor()` → `LogTailer` poll file tiap ~1 detik
6. [ ] Baris baru → `_process_log_line(line, ...)`
7. [ ] `parse_log_line()` — regex `NGINX_PATTERN` + strip/merge `POST_DATA` ke field `query`
8. [ ] `DetectionEngine.analyze(entry)` — gabung string `method path query user_agent`, match regex DB + baseline OWASP
9. [ ] Kalau match → threat dict (`attack_type`, `severity`, `matched_text`, …); kalau tidak → return `None`, selesai
10. [ ] Dedup: skip jika IP+attack_type sama sudah ada incident dalam **5 menit** (kecuali waiver unblock)
11. [ ] Buat row `Incident` di PostgreSQL, commit, `rule.match_count++` kalau rule DB aktif
12. [ ] `responder.respond(threat, incident.id)` → **Section 4** (block / rate-limit)
13. [ ] Background thread: AbuseIPDB reputation (kalau API key ada) — **bukan** AI; AI explain manual di UI
14. [ ] Dashboard `/stats` baca tabel `incidents` → angka/chart berubah dari 0

**Mode log monitor (env):**

| Env | Perilaku |
|---|---|
| Docker Compose | `USE_SIMULATED_LOGS=false` → tail **access.log nyata** dari vuln-web |
| Dev `run.py` | Sama — `start_monitor` di `__main__` |
| `USE_SIMULATED_LOGS=true` | `SimulatedLogFeeder` — demo tanpa vuln-web (jarang dipakai production) |

**Isi `parse_log_line` output (hafal keys ini):**

| Key | Dari mana |
|---|---|
| `ip` | Client IP di baris log |
| `method` | GET / POST / … |
| `path` | Path URL (decoded) |
| `query` | Query string + **POST_DATA** digabung |
| `user_agent` | UA string |
| `status_code` | HTTP status response |
| `raw` | Baris log asli (truncated di incident) |

**Isi `analyze()` — urutan logic:**

1. Skip kalau IP di **whitelist** (`BlockedIP.is_whitelist=True`)
2. Reload rules dari DB kalau `rules_dirty` (Redis) — Section 7
3. Loop compiled regex per `attack_type` (SQL_INJECTION, XSS, PATH_TRAVERSAL, …)
4. Brute force: POST ke path login + threshold Redis (`BruteForceTracker`) — bukan regex
5. Kalau banyak match → ambil **severity tertinggi** (`score`)
6. Return threat dict atau `None`

**Attack types baseline (hardcoded di `DETECTION_PATTERNS`):**

| Type | Cara detect | Severity default |
|---|---|---|
| SQL_INJECTION | Regex di query/path/POST_DATA | critical |
| XSS | Regex tag/script/event handler | critical |
| PATH_TRAVERSAL | `../`, `/etc/passwd`, dll. | high |
| COMMAND_INJECTION | `;whoami`, `cmd=`, dll. | critical |
| FILE_UPLOAD | ekstensi berbahaya di POST_DATA | high |
| SCANNER | UA/tool scanner | medium |
| BRUTE_FORCE | threshold POST login | high |

**Pemahaman saya:**

*(isi besok — copy template di bawah, hapus yang tidak perlu)*

1. Serangan tidak langsung masuk DB — harus lewat **baris log** dulu.
2. vuln-web sengaja log **POST body** sebagai `POST_DATA:` karena banyak attack di form, bukan URL.
3. Backend tidak hook ke vuln-web — hanya **baca file** (Docker shared volume) atau terima push (`internal.py` di deploy terpisah).
4. Satu baris log = satu putaran: parse → analyze → (optional) incident.
5. Detection = **regex + rule DB**, bukan AI. AI cuma explain incident manual (Section 5).
6. Dedup 5 menit = anti spam incident identik dari IP yang sama.
7. Setelah incident dibuat, `respond()` jalan — lanjut Section 4.

**Latihan besok (~1–2 jam):**

1. [ ] `docker compose up` — buka vuln-web `:5050`, kirim SQLi sederhana (`' OR 1=1--`)
2. [ ] `docker compose logs backend` — cari `[THREAT] SQL_INJECTION from ...`
3. [ ] Buka Incidentra UI → Incidents — row baru muncul?
4. [ ] Dashboard → angka `last_24h` naik?
5. [ ] Buka `access.log` di volume / tail log — lihat format `POST_DATA:`
6. [ ] Trace 1 baris: copy log line → baca `parse_log_line` → baca `analyze` — cocok?

**Pertanyaan sidang (draft — centang kalau sudah bisa jawab):**

- Q1. Kenapa perlu `POST_DATA` di log, tidak cukup URL saja?
- Q2. Beda detection engine vs AI Groq?
- Q3. Apa yang terjadi kalau log monitor mati? (hint: banner kuning Dashboard `/log-status`)
- Q4. Bagaimana Docker Compose hubungkan vuln-web log ke backend?
- Q5. Kenapa ada dedup 5 menit?

**Jawaban:**

- A1. *(kosong — isi setelah latihan atau tanya ke AI)*
- A2.
- A3.
- A4.
- A5.

**One-liner sidang (hafalkan):**

> "vuln-web menulis access log dengan suffix POST body; backend tail file shared volume lewat log monitor, parse ke struct, lalu detection engine match regex OWASP + rule DB; jika threat, buat incident PostgreSQL dan trigger automated response."

---

## 4. Automated Response (block / rate-limit / escalation)

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/core/response_manager.py` | `Ctrl+F` → `respond`, `_escalating_block`, `_write_blocked_ips_json`, `_apply_rate_limit` |
| Target app | `vuln-web/middleware/security.py` | *(baca blocked_ips.json / rate_limited.json)* |

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 5. Incident Detail + AI Explanation (Groq)

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/api/incidents.py` | `Ctrl+F` → `trigger_explanation`, `simulate` |
| Backend | `backend/app/services/ai_service.py` | `Ctrl+F` → `_call_groq_with_fallback`, `generate_explanation_task`, `_save_fallback_explanation` |

**Catatan penting (sudah terverifikasi ke kode, bukan asumsi):** `trigger_explanation` di `incidents.py` **selalu jalan sinkron** dalam request/response yang sama — tidak ada Celery, tidak ada thread terpisah, di jalur ini. `generate_explanation_task` di `ai_service.py` didaftarkan sebagai Celery task tapi tidak pernah dipanggil `.delay()` di manapun pada kode saat ini.

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 6. IP Management (Blocked / Rate Limited / Whitelist)

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/api/blocked_ips.py` | *(belum ada Ctrl+F anchor)* |
| Backend | `backend/app/api/rate_limited.py` | *(belum ada Ctrl+F anchor)* |

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 7. Detection Rules CRUD + rules_dirty reload

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/api/rules.py` | `Ctrl+F` → `update_rule` (is_active toggle), `create_rule` |
| Backend | `backend/app/core/detection_engine.py` | `_load_rules_from_db`, `_maybe_reload_rules`, `rules_dirty` |

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 8. Notifications (Email/Telegram) + AbuseIPDB

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/core/response_manager.py` | `_notify_async` |
| Backend | `backend/app/services/notification_service.py` | `_do_notify` |
| Backend | `backend/app/services/threat_intel_service.py` | `check_ip_reputation`, `_do_reputation_check` |
| Backend | `backend/app/core/log_monitor.py` | baris yang spawn thread `_do_reputation_check` |

**Catatan penting (terverifikasi ke kode):** Notifikasi dan AbuseIPDB **tidak lewat Celery** — keduanya dipanggil lewat `threading.Thread(daemon=True)` yang di-spawn langsung dari `response_manager.py` (notifikasi) dan `log_monitor.py` (AbuseIPDB), segera setelah incident dibuat. Celery Worker di project ini **hanya** menjalankan satu task nyata: `cleanup_expired_blocks` (jadwal per jam via Celery Beat, lihat `backend/celery_worker.py`) — tidak terkait AI, notifikasi, atau AbuseIPDB sama sekali.

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 9. Settings + User Management (RBAC) + Audit Log

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/api/settings.py` | *(belum ada Ctrl+F anchor)* |
| Backend | `backend/app/api/users.py` | *(belum ada Ctrl+F anchor)* |
| Backend | `backend/app/api/audit.py` | *(belum ada Ctrl+F anchor)* |

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 10. Docker Compose — bagaimana 6 service saling terhubung

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Root | `docker-compose.yml` | nama tiap service, `volumes:`, `depends_on:` |
| Backend | `backend/docker_entrypoint.sh` | urutan startup (migrate → seed → gunicorn) |
| Backend | `backend/celery_worker.py` | `cleanup_expired_blocks`, `beat_schedule` |

**Alur:**

1.
2.
3.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## Log perubahan (changelog) — supaya kejadian "lupa pernah improvement" tidak terulang

> Isi baris baru tiap kali ada perubahan arsitektur/implementasi signifikan yang mungkin bikin laporan/diagram jadi tidak sinkron dengan kode. Cukup 1 baris.

| Tanggal | Perubahan | File terdampak |
|---|---|---|
| 2026-08-01 | Dokumentasi pemahaman Login + Dashboard CHART 1; komentar Ctrl+F di Dashboard.js | `docs/PEMAHAMAN_PROGRESSIF.md`, `Dashboard.js` |
| 2026-08-01 | Kerangka Section 3 Log Ingestion → Detection (diagram, alur 14 langkah, latihan besok) | `docs/PEMAHAMAN_PROGRESSIF.md` |
