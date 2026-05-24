# SME-Guard — Operational Guide

Single guide: **run** the system (Docker or manual), **defense demo**, and **troubleshooting**.

**Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Detection:** [DETECTION.md](DETECTION.md) · **Full audit:** [AUDIT.md](AUDIT.md)

**Repo:** [github.com/HardInCode/sme-guard](https://github.com/HardInCode/sme-guard)

---

## Prasyarat


| Mode       | Yang dibutuhkan                                             |
| ---------- | ----------------------------------------------------------- |
| **Docker** | Docker Desktop **Running** (hijau)                          |
| **Manual** | Python 3.10–3.13 · Node 18–20 LTS · PostgreSQL 15 · Redis 7 |


---

## Yang akan berjalan

```
PostgreSQL + Redis
        │
        ▼
Backend (Flask :5000) ◄── tail access.log vuln-web
        │
        ▼
Frontend (React :3000)     vuln-web (:5050) ──► logs/access.log
                              └── blocked_ips.json, rate_limited.json
```


| Layanan       | URL                                                    |
| ------------- | ------------------------------------------------------ |
| SOC Dashboard | [http://localhost:3000](http://localhost:3000)         |
| Backend API   | [http://localhost:5000/api](http://localhost:5000/api) |
| Vuln-web      | [http://localhost:5050](http://localhost:5050)         |


**Login SOC:** `admin` / `Admin@Incidentra2026!` · analyst / `Analyst@Incidentra2026!`

---

## File environment


| File                          | Dipakai                         | Jangan                              |
| ----------------------------- | ------------------------------- | ----------------------------------- |
| `backend/.env.example`        | Template manual                 | Commit sebagai `.env` dengan secret |
| `backend/.env`                | Manual `python run.py`          | Push ke GitHub                      |
| `backend/.env.docker.example` | Template Docker                 | —                                   |
| `backend/.env.docker`         | Docker compose                  | Push jika berisi API key            |
| `vuln-web/.env.example`       | Template lab target             | —                                   |
| `vuln-web/.env`               | Manual `python app.py` (Fase 3) | Push ke GitHub                      |
| `docker-compose.yml`          | URL DB/Redis container          | Edit `localhost` untuk DB di Docker |


**Docker:** `DATABASE_URL` di `docker-compose.yml`, bukan di `.env.docker`.  
**Fase 3 di Docker:** `vuln-web/.env` **tidak** otomatis dibaca container — tambahkan variabel di `docker-compose.yml` service `vuln_web` (lihat § Fase 3) atau demo Fase 3 pakai **manual**.

### Variabel `vuln-web/.env` (Mei 2026)

Salin dari `vuln-web/.env.example` → `vuln-web/.env`. Nilai **aktif** untuk flag boolean: `1`, `true`, atau `yes` (huruf besar/kecil). Nilai lain / kosong = **mati** (sama seperti `0`).


| Variabel                 | Default                  | Jika `=1` (atau true/yes)                                                     |
| ------------------------ | ------------------------ | ----------------------------------------------------------------------------- |
| `VULN_PORT`              | `5050`                   | Port Flask                                                                    |
| `VULN_LOG_FILE`          | `logs/access.log`        | Path access log                                                               |
| `BLOCKED_IPS_JSON`       | `logs/blocked_ips.json`  | File blokir (baca middleware)                                                 |
| `RATE_LIMITED_JSON`      | `logs/rate_limited.json` | File rate limit                                                               |
| `**VULN_UNSAFE_CMD`**    | **off**                  | `/cmd` menjalankan **shell nyata** (`subprocess`, timeout `VULN_CMD_TIMEOUT`) |
| `**VULN_UNSAFE_UPLOAD`** | **off**                  | Upload `/files` boleh **path escape** (`../` di nama file)                    |
| `VULN_CMD_TIMEOUT`       | `5`                      | Detik (hanya jika `VULN_UNSAFE_CMD=1`)                                        |


**Penting:**

- Edit `.env` → **wajib restart** vuln-web (`Ctrl+C` → `python app.py`). Refresh browser **tidak** cukup.
- `VULN_UNSAFE_CMD=1` **tidak** mengubah deteksi/blokir SOC — hanya output di halaman lab. Blokir tetap: insiden **COMMAND_INJECTION** di backend → `blocked_ips.json`.
- Tanpa flag: `/cmd` mode **simulated**; upload profil **avatar tanpa filter ekstensi** (skenario CTF) tetap ada di `/profile`.

---

## Jalankan — Docker (disarankan)

```powershell
git clone https://github.com/HardInCode/sme-guard.git
cd sme-guard
copy backend\.env.docker.example backend\.env.docker
docker compose up --build -d
docker compose ps
```

Tunggu ~2 menit. Semua service harus **running**.

**Volume `vuln_logs`:** backend `/app/watched_logs/` = vuln-web `/app/logs/`.

```powershell
docker compose logs backend --tail 30
```

Harus ada: `PostgreSQL ready`, `DB init complete`, `Log monitor started`.

**Stop:** `docker compose down`

### Troubleshooting Docker


| Masalah                          | Solusi                                                          |
| -------------------------------- | --------------------------------------------------------------- |
| `dockerDesktopLinuxEngine` gagal | Jalankan Docker Desktop dulu                                    |
| Port 3000/5000/5050 dipakai      | Tutup proses manual atau `docker compose down`                  |
| Backend restart loop             | `docker compose logs backend` — cek `postgresql+psycopg`        |
| Build frontend `ajv` error       | `docker compose build --no-cache frontend`                      |
| UI tidak panggil API             | Rebuild frontend; `REACT_APP_API_URL=http://localhost:5000/api` |


---

## Jalankan — Manual (3 terminal)

### PostgreSQL & Redis

```powershell
psql -U postgres -f scripts/init_postgres.sql
redis-cli ping
```

Harus `PONG`.

### Terminal 1 — Backend

```powershell
cd backend
copy .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

First run (simulasi): `USE_SIMULATED_LOGS=true`, `DEMO_MODE=true` di `.env`.

### Terminal 2 — Frontend

```powershell
cd frontend
npm install
npm start
```

Opsional grafik: `python scripts/seed_chart_demo.py` (venv backend, dari root).

### Terminal 3 — vuln-web

```powershell
cd vuln-web
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

### Sambungkan log nyata

Edit `backend\.env`:

```env
USE_SIMULATED_LOGS=false
DEMO_MODE=false
WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
BLOCKED_IPS_JSON_PATH=../vuln-web/logs/blocked_ips.json
RATE_LIMITED_JSON_PATH=../vuln-web/logs/rate_limited.json
```

Restart backend. Log: `Tailing real log: ...`

---

## Skrip utilitas & reset demo

### Manual (dari root repo)

Venv backend aktif (`pip install psycopg redis` jika belum):


| Perintah                                        | Fungsi                                      |
| ----------------------------------------------- | ------------------------------------------- |
| `python scripts/reset_smeguard.py`              | Kosongkan insiden, blokir, rate JSON, Redis |
| `python scripts/reset_smeguard.py --clear-logs` | + kosongkan `vuln-web/logs/access.log`      |
| `python scripts/seed_chart_demo.py`             | Grafik dashboard 7 hari                     |


Setelah reset → restart backend + vuln-web.

### Docker (stack `docker compose up` sedang jalan)

Log & JSON blokir ada di **volume Docker** `vuln_logs`, bukan di folder `vuln-web/logs/` di Windows. Script reset di host **tetap bisa** kosongkan DB + Redis (port 5432/6379 di-expose), lalu kosongkan file di container:

```powershell
cd E:\Capstone\May\sme-guard-May

Script reset
cd E:\Capstone\May\sme-guard-May
docker compose up -d
.\scripts\reset_smeguard_docker.ps1 -ClearLogs

# 2) access.log + JSON di volume (wajib lewat container)
docker compose exec vuln_web sh -c ":> /app/logs/access.log"
docker compose exec vuln_web sh -c 'echo "{\"blocked\":[],\"details\":{},\"updated_at\":\"\"}" > /app/logs/blocked_ips.json'
docker compose exec vuln_web sh -c 'echo "{\"rate_limited\":[],\"updated_at\":\"\"}" > /app/logs/rate_limited.json'

# 3) Agar tail log backend bersih
docker compose restart backend vuln_web
```

**Alternatif keras** (hapus semua data volume termasuk DB): `docker compose down -v` lalu `docker compose up --build -d` — hanya jika Anda OK database kosong total.

**Grafik demo di Docker:** jalankan `seed_chart_demo.py` dengan `$env:DATABASE_URL` yang sama seperti di atas (lihat § di bawah).

---

## Simulate Attack — Mode A vs Mode B (Inject log)

Ini **bukan** perintah `docker compose exec` ke file log. Inject log lewat **API backend** (tombol di SOC atau `curl`), yang menulis ke volume `vuln_logs` **dan** langsung menjalankan detection engine.

### Mode A — Direct Simulation (instan)

1. Login SOC → **Incidents** → **Simulate Attack**
2. Pilih **Mode A — Direct Simulation**
3. Pilih attack type → **Launch**

Insiden langsung masuk PostgreSQL (tanpa baca `access.log`). Cocok untuk uji UI.

### Mode B — Log Injection (pipeline penuh) — **disarankan Docker**

1. Pastikan stack jalan: `docker compose up -d`
2. Login `http://localhost:3000` (`admin` / `Admin@Incidentra2026!`)
3. **Incidents** → **Simulate Attack**
4. Pilih **Mode B — Log Injection**
5. Attack type mis. **LFI/RFI** atau **SQL Injection**
6. **Source IP:** ganti jika pernah tes IP yang sama < 5 menit lalu (mis. `203.0.113.99`)
7. **Launch**


| Hasil toast                                   | Artinya                                                                                   |
| --------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Hijau: `Log injected — N incident(s) created` | Berhasil — refresh tabel; insiden + blokir (jika critical)                                |
| Kuning: `no new incident (duplicate...)`      | Log tertulis, tapi IP + attack type sama dalam 5 menit → **ganti IP** atau tunggu 5 menit |
| Merah: `Could not write to log file`          | Backend tidak bisa tulis volume — cek `docker compose ps`, restart `backend`              |


**Bukan** menunggu 5 detik tailer — backend memproses baris **langsung** lewat `ingest_log_lines`. Live Traffic bisa terisi saat tailer membaca baris yang sama (~1–3 s).

### Mode B lewat PowerShell (debug, Docker)

```powershell
$body = @{ username = "admin"; password = "Admin@Incidentra2026!" } | ConvertTo-Json
$login = Invoke-RestMethod -Method POST -Uri "http://localhost:5000/api/auth/login" `
  -ContentType "application/json" -Body $body
$headers = @{ Authorization = "Bearer $($login.token)" }

$inject = @{ attack_type = "LFI_RFI"; ip = "203.0.113.77" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri "http://localhost:5000/api/detection/inject-log" `
  -Headers $headers -ContentType "application/json" -Body $inject
```

Respons sukses berisi `incident_ids` (array tidak kosong).

### Jangan dicampur dengan ini


| Yang Anda coba                                             | Masalah                                                                                                                                                                    |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docker compose exec vuln_web` append ke `access.log` saja | Backend **tidak** otomatis proses tanpa tailer/inject API; path di container vuln-web = `/app/logs/access.log` (volume sama dengan backend `/app/watched_logs/access.log`) |
| `seed_chart_demo.py` tanpa `DATABASE_URL`                  | Error `password authentication failed` — Postgres Docker pakai user/pass di compose (lihat bawah)                                                                          |
| Mode B dengan IP `45.33.32.156` berulang                   | Dedup 5 menit → ganti IP di dialog                                                                                                                                         |


### `seed_chart_demo.py` — isi grafik 7 hari (bukan Mode B)

**Tujuan:** insiden di PostgreSQL dengan `created_at` **berbeda per hari** (timeline + donut severity).  
**Bukan** tombol Simulate Attack Mode B (itu pipeline detection + log satu baris).

**Penting (Windows):** `localhost:5432` sering = **PostgreSQL Windows** (`backend/.env`: `postgres` / `sme_guard_db`), **bukan** database Docker (`smeguard` / `smeguard_db`). Dashboard Docker membaca DB container — seed dari host dengan `$env:DATABASE_URL=smeguard...` bisa gagal (`password authentication failed`).

**Cara yang benar saat pakai Docker Compose:**

```powershell
cd E:\Capstone\May\sme-guard-May
docker compose up -d
.\scripts\seed_chart_docker.ps1
# Cek rencana dulu:
.\scripts\seed_chart_docker.ps1 -DryRun
```

**Cara manual** (backend `python run.py` + Postgres di `backend/.env`):

```powershell
python scripts/seed_chart_demo.py
python scripts/seed_chart_demo.py --dry-run
```

Lalu refresh Dashboard (`http://localhost:3000`).


| Opsi            | Fungsi                                                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| (default)       | Insert ~15–25 insiden, `created_at` tersebar 7 hari                                                                            |
| `--dry-run`     | Tampilkan rencana, tanpa tulis DB                                                                                              |
| `--append-logs` | Plus baris di `access.log` (Live Traffic); **jangan** pakai saat backend tail aktif jika tidak ingin insiden tambahan hari ini |


Sebelum demo live (bukan grafik), kosongkan insiden lama: `.\scripts\seed_chart_docker.ps1` hanya untuk grafik — atau `reset_smeguard.py` + restart. Insiden seed lama bisa memicu toast bell IP `203.0.113.x` dengan tanggal yang membingungkan.

**AI Explanation:** hanya muncul setelah klik **Generate AI Explanation** di detail insiden — tidak otomatis saat deteksi / inject log.

**Docker vs manual — kapan ubah `DATABASE_URL`?**


| Situasi                                                  | `DATABASE_URL` untuk skrip di PowerShell                                         |
| -------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Docker** Postgres di `localhost:5432`, user `smeguard` | `postgresql://smeguard:smeguard123@localhost:5432/smeguard_db` (seperti di atas) |
| **Manual** backend pakai `backend/.env` yang sama        | **Sama** — tidak perlu ubah, atau hapus `$env:` dan biarkan skrip baca `.env`    |
| **Manual** Postgres lain (user/password beda)            | Samakan dengan baris `DATABASE_URL` di `backend/.env`                            |


`REDIS_URL` hanya dipakai jika backend/app butuh Redis saat skrip jalan; untuk `seed_chart_demo` yang utama adalah **DATABASE_URL**. Backend `python run.py` manual tetap baca `backend/.env` — tidak otomatis ikut `$env` di terminal kecuali Anda export sebelum `python run.py`.

**Ringkas:** Kalau Postgres/Redis tetap di `localhost` dengan kredensial `smeguard` / `smeguard123`, **satu set URL cukup** untuk Docker dan untuk menjalankan skrip dari host. Ubah hanya jika Anda ganti ke database manual dengan kredensial berbeda.

---

## IP Management

Menu: **IP Management** (`/blocked-ips`).


| Tab              | Fungsi                                                                    |
| ---------------- | ------------------------------------------------------------------------- |
| **Blocked**      | Blokir permanen/sementara, edit durasi, unblock (DB + `blocked_ips.json`) |
| **Rate Limited** | Daftar IP rate limit, **Clear**, **Extend**                               |


Unblock di tab Blocked juga menghapus rate limit untuk IP tersebut.

---

## Banner "No logs in 60s" (Dashboard)

Banner ini = backend **belum menerima aktivitas log** dalam 60 detik (bukan berarti vuln-web mati).


| Mode                         | Cara kerja                                                                                                                                          |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Docker**                   | Log monitor jalan di proses terpisah (`docker_log_monitor.py`). Heartbeat disimpan di **Redis** + cek **mtime** `access.log` di volume `vuln_logs`. |
| **Manual** (`python run.py`) | Satu proses — heartbeat in-memory, sama seperti Redis jika Redis jalan.                                                                             |


**Agar hilang:** buka shop `http://localhost:5050` (beberapa halaman), tunggu ~5 detik, refresh Dashboard.


| Gejala                         | Penyebab                                         | Solusi                                                                                                 |
| ------------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| Banner tetap meski shop dibuka | Backend image lama (sebelum perbaikan heartbeat) | `docker compose up --build -d backend`                                                                 |
| Banner + Live Traffic kosong   | Volume log tidak shared / vuln-web mati          | `docker compose ps`; cek `docker compose exec vuln_web tail -3 /app/logs/access.log`                   |
| Manual: banner tetap           | `USE_SIMULATED_LOGS=true` atau path log salah    | `.env`: `USE_SIMULATED_LOGS=false`, `WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log`, restart backend |


---

## Tiga lapisan: Live Traffic ≠ Insiden ≠ Blokir


| Lapisan                 | Di UI                             | Artinya                                                                |
| ----------------------- | --------------------------------- | ---------------------------------------------------------------------- |
| **A. Log**              | Live Traffic                      | Setiap HTTP ke vuln-web → `access.log`                                 |
| **B. Tag**              | Live Traffic kolom TAG            | Heuristik cepat (`cmd=` → **Attack**) — **bukan** keputusan SOC        |
| **C. Insiden + blokir** | **Incidents** + **IP Management** | `DetectionEngine` → PostgreSQL + `blocked_ips.json` → vuln-web **403** |


**Gejala umum:** baris **Attack** status **200** = pola terlihat di log, **belum tentu** ada insiden. Tanpa insiden → **tidak ada** blokir permanen.

**Setelah blokir benar:** request baru ke vuln-web → **403**, tag **Blocked** di Live Traffic.

**IP yang diblokir** = IP di kolom Live Traffic (bisa `192.168.x.x`, bukan selalu `127.0.0.1`).

---

## Mode Lab deteksi & baseline OWASP


| Mode                 | Setting          | Deteksi                                                                           |
| -------------------- | ---------------- | --------------------------------------------------------------------------------- |
| Produksi (default)   | Lab mode **OFF** | Rule aktif di UI **+** regex bawaan `DETECTION_PATTERNS` di `detection_engine.py` |
| Sidang (rule kustom) | Lab mode **ON**  | **Hanya** rule aktif di Detection Rules                                           |


Peta file untuk sidang: [DETECTION.md](DETECTION.md).

**Contoh rule kustom SQLi:** pattern `(?i)lorem\s+ipsum` → POST login dengan `username=lorem ipsum` → insiden **SQL_INJECTION** (rule Anda, `match_count` naik).

**Toggle rule OFF** di UI (lab mode OFF): deteksi bisa tetap jalan dari **baseline**, bukan dari rule DB — itu normal.

---

## HTTP 429 (kuning) vs 403 (merah)


| Kode    | Penyebab                                                                         |
| ------- | -------------------------------------------------------------------------------- |
| **403** | IP di `blocked_ips.json` (critical/high block)                                   |
| **429** | IP di `rate_limited.json` + terlalu banyak request dalam jendela (mis. 10/menit) |


Cara memicu 429: serangan **SCANNER** (User-Agent Nikto/sqlmap) → severity medium → rate limit, lalu refresh vuln-web berkali-kali. Tab **IP Management → Rate Limited** menampilkan IP; chip “JSON only” = enforcement lewat file, TTL Redis kosong (lihat tooltip).

---

## Demo sidang — persiapan

### Terminal (manual)

```powershell
# T1 — Backend
cd backend
.\venv\Scripts\Activate.ps1
# .env: USE_SIMULATED_LOGS=false, WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
python run.py

# T2 — vuln-web
cd vuln-web
.\venv\Scripts\Activate.ps1
python app.py

# T3 — Frontend (opsional)
cd frontend
npm start
```

### Reset (disarankan sebelum demo)

- **Manual:** `python scripts/reset_smeguard.py --clear-logs` → restart backend + vuln-web.
- **Docker:** ikuti § **Skrip utilitas — Docker** di atas (bukan `--clear-logs` saja di host).

### Cek IP Anda

Buka `http://localhost:5050/` — di Live Traffic lihat kolom **IP**. Itu IP yang akan diblokir.

---

## Demo sidang — langkah demi langkah

### 1. SQL Injection → blokir permanen

1. Unblock IP di SOC → **IP Management** → tab Blocked (jika ada).
2. Browser: `http://localhost:5050/login`
3. Username: `admin' OR '1'='1' --` , password: apa saja → Submit.
4. Tunggu 5–10 detik.
5. SOC → **Incidents** → **SQL_INJECTION**, critical.
6. Refresh `http://localhost:5050/` → **403 Forbidden SME-Guard**.

### 2. XSS

1. Unblock IP.
2. `http://localhost:5050/search?q=<script>alert(1)</script>`
3. Incidents → **XSS** → refresh vuln-web → **403**.

### 3. Command injection

Gunakan **salah satu** (setelah **restart backend** `python run.py` jika baru update deteksi):

```
http://localhost:5050/cmd?cmd=;whoami
http://localhost:5050/cmd?cmd=whoami
http://localhost:5050/cmd?cmd=whoami%20%26%20id
```

**Expected:** Incidents → **COMMAND_INJECTION**, critical → vuln-web **403** pada request berikutnya.

### 4. Scanner & brute force (ringkas)


| Serangan    | Langkah                                        | Expected                                           |
| ----------- | ---------------------------------------------- | -------------------------------------------------- |
| Scanner     | `curl -A "Nikto/2.1.6" http://localhost:5050/` | **SCANNER**, medium, rate limit (tab Rate Limited) |
| Brute force | 12× POST login gagal                           | **BRUTE_FORCE**, high, temporary block             |


### 5. Upload berbahaya vs aman


| Tes       | Langkah                                                      | Expected                                           |
| --------- | ------------------------------------------------------------ | -------------------------------------------------- |
| Aman      | `/files` POST `notes.txt`                                    | Hanya Live Traffic — **tanpa** insiden FILE_UPLOAD |
| Berbahaya | `/files` POST `shell.php` atau `/profile` avatar `shell.php` | **FILE_UPLOAD**, high, temporary block             |


### 6. Urutan demo sidang (~15 menit)

1. Dashboard SOC (bersih).
2. vuln-web shop (normal).
3. SQLi login → insiden → 403.
4. Unblock → XSS search → insiden → 403.
5. Unblock → `cmd?cmd=;whoami` → insiden → 403.
6. (Opsional) Fase 3: banner + output shell.
7. Live Traffic: Attack vs Blocked + hide static.
8. IP Management: blocked list + unblock.

---

## Fase 3 lab (`VULN_UNSAFE_CMD` / `VULN_UNSAFE_UPLOAD`)

File: `vuln-web/.env` (buat dari `.env.example` jika belum ada):

```env
VULN_UNSAFE_CMD=1
# VULN_UNSAFE_UPLOAD=1
# VULN_CMD_TIMEOUT=5
```

**Wajib restart vuln-web** setelah edit (Ctrl+C → `python app.py`).  
Cek: banner merah di shop + halaman `/cmd` bertuliskan **Live shell enabled**.

**Docker (opsional Fase 3):** tambah di `docker-compose.yml` pada service `vuln_web` → `environment:`:

```yaml
VULN_UNSAFE_CMD: "1"
# VULN_UNSAFE_UPLOAD: "1"
```

Lalu `docker compose up -d --build vuln_web`.

### Demo command (Fase 3)

1. Reset + unblock IP.
2. Shop — **banner merah** "Phase 3 lab mode active".
3. `http://localhost:5050/cmd?cmd=;whoami` → output **shell nyata** (bukan "Simulated").
4. SOC **Incidents** → **COMMAND_INJECTION** (bukan hanya Live Traffic).
5. Refresh vuln-web → **403**; Live Traffic baris terbaru → **Blocked**.

### Demo upload (Fase 3, opsional)

1. Set `VULN_UNSAFE_UPLOAD=1`, restart vuln-web.
2. Unblock IP → `/files` → upload `shell.php` → insiden **FILE_UPLOAD**.
3. Upload `notes.txt` → hanya Live Traffic, tanpa insiden.

---

## OWASP upload & FILE_UPLOAD (ringkas)


| Standar              | Label                                             |
| -------------------- | ------------------------------------------------- |
| OWASP Top 10         | A04 — Insecure Design / misconfig upload          |
| CWE                  | **CWE-434** Unrestricted Upload of Dangerous Type |
| MITRE (di SME-Guard) | **T1105** Ingress Tool Transfer                   |


**Deteksi SME-Guard:** insiden hanya jika log punya `file=` atau `avatar=` + ekstensi berbahaya (`.php`, `.jsp`, dll.). Upload `.jpg` / `.txt` → log saja.

Detail lab path traversal: [DETECTION.md](DETECTION.md) § Security Lab.

---

## Status pengembangan (Mei 2026)


| Fase                     | Isi                                                                 | Status |
| ------------------------ | ------------------------------------------------------------------- | ------ |
| Core SOC + vuln-web shop | Backend, frontend, deteksi, IP mgmt                                 | Done   |
| Fase 2                   | `/files` read + upload, FILE_UPLOAD (ekstensi berbahaya)            | Done   |
| Fase 3                   | `VULN_UNSAFE_CMD`, `VULN_UNSAFE_UPLOAD`, avatar profil tanpa filter | Done   |
| Form 4                   | Dokumentasi & screenshot                                            | Tim    |


---

## Troubleshooting


| Masalah                                        | Penyebab                            | Solusi                                                                                                                             |
| ---------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Live Traffic **Attack 200**, tidak ada insiden | Tag heuristik ≠ insiden SOC         | Restart backend `run.py`; cek **Incidents**; pakai `;whoami`                                                                       |
| Tidak ada insiden sama sekali                  | Log tidak ke-tail                   | `USE_SIMULATED_LOGS=false`, path log benar, restart backend                                                                        |
| Insiden ada, tidak 403                         | IP beda (LAN vs 127.0.0.1)          | Unblock IP yang benar di kolom Live Traffic                                                                                        |
| 403 terus                                      | Masih di `blocked_ips.json`         | Unblock di SOC atau `reset_smeguard.py --clear-logs`                                                                               |
| Fase 3 tidak shell nyata                       | `.env` tidak dibaca / belum restart | Pastikan file `vuln-web/.env` ada; `VULN_UNSAFE_CMD=1`; restart `python app.py`; halaman `/cmd` harus tulis **Live shell enabled** |
| Fase 3 di Docker tidak jalan                   | Container tanpa env Fase 3          | Tambah `VULN_UNSAFE_CMD: "1"` di `docker-compose.yml` atau demo manual                                                             |
| Database / Redis error                         | Service mati                        | Cek `DATABASE_URL`, `redis-cli ping`                                                                                               |
| Banyak insiden duplikat                        | Dedup 5 menit per IP+type           | Normal                                                                                                                             |


---

## Langkah berikutnya

- [ARCHITECTURE.md](ARCHITECTURE.md) — arsitektur & API
- [AUDIT.md](AUDIT.md) — audit full sidang (Mei 2026)
- [GITHUB.md](GITHUB.md) — push tim
- [LEARNING.md](LEARNING.md) — JWT, konsep Bab 3

