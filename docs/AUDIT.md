# Audit Full SME-Guard (Incidentra) — Mei 2026

**Versi:** Audit lengkap capstone · **Mei 2026**  
**Produk:** Intelligent Web-SOC Platform with Automated Incident Response  
**Scope:** Demo lokal (manual 3-terminal **atau** Docker Compose). Deploy VPS **tidak** wajib.

**Cara pakai:** Jalankan bagian **P** lalu **A** atau **D**, serangan **B**/**E**, opsional **C** (Burp), fitur **F**–**J**, revisi **G**. Centang **Pass** jika *expected result* terpenuhi.

| Field | Isi |
|-------|-----|
| **Tester** | _______________ |
| **Tanggal uji** | _______________ |
| **Lingkungan** | ☐ Manual  ☐ Docker Desktop |
| **OS** | Windows / Linux / macOS ___ |
| **Commit / tag** | _______________ |

**Guide:** [GUIDE.md](GUIDE.md) · **Detection:** [DETECTION.md](DETECTION.md) · **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Form 4:** [form4/FORM4_IMPLEMENTATION_v2.md](form4/FORM4_IMPLEMENTATION_v2.md)

---

## Daftar isi

| Bagian | Isi |
|--------|-----|
| [Konsep](#konsep-audit) | Live Traffic vs insiden vs blokir; baseline vs AI vs lab mode |
| [P](#p--persiapan-umum) | Persiapan umum |
| [A](#a--setup-manual) | Setup manual |
| [B](#b--serangan-manual) | Serangan manual (8 tipe + unblock + AI) |
| [C](#c--burp-suite) | Burp Suite (opsional sidang) |
| [D](#d--setup-docker) | Setup Docker |
| [E](#e--serangan-docker) | Serangan Docker (ulang B) |
| [F](#f--fitur-soc) | Fitur SOC (dashboard, traffic, rules, IP, export, …) |
| [G](#g--shop-upload-fase-3) | Shop, upload, path absolut, Fase 3 |
| [H](#h--settings--integrasi) | Settings, threshold, Groq, notifikasi |
| [I](#i--lab-mode--rule-kustom) | Lab mode & rule kustom (demo sidang) |
| [J](#j--uiux--mei-2026) | UI/UX Mei 2026 (chatbot, toast, dialog rules) |
| [Ringkasan](#ringkasan-penilaian) | Keputusan lulus / gagal |

---

## Konsep audit

### Tiga lapisan (wajib paham)

| Lapisan | UI | Arti |
|---------|-----|------|
| **1. Log** | Live Traffic | Setiap HTTP → `access.log` |
| **2. Tag** | Live Traffic TAG | Heuristik cepat (`traffic.py`) — **bukan** keputusan SOC |
| **3. Insiden + blokir** | Incidents + IP Management | `DetectionEngine` → PostgreSQL → `blocked_ips.json` → vuln-web **403** |

**Lulus serangan** = tipe & severity benar di **Incidents** **dan** (kecuali rate limit) **403** pada request berikutnya dari IP yang sama. **Attack 200** saja = **tidak cukup**.

**IP yang diblokir** = IP di kolom Live Traffic (`172.x`, `192.168.x`, dll.). **Unblock** IP itu sebelum tes berikutnya.

### Tiga sumber deteksi (sidang)

| Sumber | File / UI | Kapan aktif |
|--------|-----------|-------------|
| **Rule UI** | Detection Rules → PostgreSQL | Rule `is_active=true` |
| **Baseline OWASP** | `detection_engine.py` → `DETECTION_PATTERNS` | Default (Lab mode **OFF**) |
| **AI analyst** | `ai_service.py` (Groq) | Hanya penjelasan insiden — **tidak** memblokir |

**Lab mode ON** (Settings): hanya rule UI; baseline mati. Lihat [I](#i--lab-mode--rule-kustom).

### Severity → respons

| Severity | Respons | vuln-web |
|----------|---------|----------|
| low | Log & monitor | 200 |
| medium | Rate limit | **429** jika melebihi kuota |
| high | Blokir sementara (~24 jam, Settings) | **403** |
| critical | Blokir permanen | **403** |

| Attack type | Severity default | Respons |
|-------------|------------------|---------|
| SQL_INJECTION | critical | Permanen |
| XSS | critical | Permanen |
| COMMAND_INJECTION | critical | Permanen |
| LFI_RFI | critical | Permanen |
| BRUTE_FORCE | high | Sementara |
| PATH_TRAVERSAL | high | Sementara |
| FILE_UPLOAD | high | Sementara |
| SCANNER | medium | Rate limit |

---

## P — Persiapan umum

| # | Langkah | Expected result | Pass | Catatan |
|---|---------|-----------------|------|---------|
| P1 | Redis: `redis-cli ping` **atau** `docker compose ps` | `PONG` / 6 service **Up** | | |
| P2 | Reset demo: `python scripts/reset_smeguard.py --clear-logs` (+ unblock semua IP) | Inciden kosong; `blocked_ips.json` kosong | | Docker: lihat [GUIDE.md](GUIDE.md) reset |
| P3 | Login SOC `admin` / `Admin@Incidentra2026!` | Dashboard, sidebar lengkap | | |
| P4 | Backend: log `Tailing real log` (bukan simulated) | Monitor aktif | | `USE_SIMULATED_LOGS=false` |
| P5 | Cari `SIDANG Ctrl+F` di `detection_engine.py`, `traffic.py` | Peta kode sidang tersedia | | Opsional — lihat [DETECTION.md](DETECTION.md) |
| P6 | Burp (jika pakai C): proxy `127.0.0.1:8080`, UA browser normal | Tidak langsung SCANNER | | |

---

## A — Setup MANUAL

Prasyarat: [GUIDE.md](GUIDE.md) Opsi B.

| # | Langkah | Expected result | Pass | Catatan |
|---|---------|-----------------|------|---------|
| A1 | `backend`: `.env`, `pip install`, `python run.py` | Seed admin/rules; `Running on :5000` | | |
| A2 | `frontend`: `npm install`, `npm start` | `:3000` login OK | | |
| A3 | `vuln-web`: `python app.py` | Shop Home/Catalog/Cart; CSS load | | |
| A4 | Backend `WEB_SERVER_LOG_PATH` → `vuln-web/logs/access.log` | `Tailing real log: ...` | | Restart setelah ubah .env |
| A5 | `http://localhost:5050/search?q=test` | Live Traffic baris baru; tanpa insiden critical | | |
| A6 | API tanpa JWT → `/api/incidents` | `401 Authorization required` | | |
| A7 | Analyst login (jika ada user analyst) | Akses terbatas vs admin | | Opsional |

---

## B — Serangan MANUAL

**Sebelum blok permanen:** unblock IP di **IP Management → Blocked**.

| # | Serangan | Langkah | Expected (≤10 s di Incidents) | Pass | Catatan |
|---|----------|---------|-------------------------------|------|---------|
| B1 | SQL Injection | POST `/login` user `admin' OR '1'='1' --` | **SQL_INJECTION** critical → **403** refresh `/` | | |
| B2 | XSS | `/search?q=<script>alert(1)</script>` | **XSS** critical → **403** | | |
| B3 | Path traversal | `/files?file=../../etc/passwd` | **PATH_TRAVERSAL** high, temp block | | Bisa LFI dulu — lihat C7 |
| B4 | Command injection | `/cmd?cmd=;whoami` atau `cmd=whoami` | **COMMAND_INJECTION** critical → **403** | | |
| B5 | Scanner | `curl -A "Nikto/2.1.6" http://localhost:5050/` | **SCANNER** medium; tab **Rate Limited** | | Bukan permanent block |
| B6 | Brute force | 12× POST `/login` password salah <60 s | **BRUTE_FORCE** high | | Threshold default 10 |
| B7 | Unblock UI | IP Management → Unblock | `localhost:5050` **200** shop | | |
| B8 | Simulate Mode B | Incidents → Simulate → LFI_RFI / FILE_UPLOAD | Toast OK; insiden ~5 s | | Tanpa vuln-web |
| B9 | Resolve workflow | Mark **resolved** | Hilang dari ongoing; ada di `/incidents/all` | | |
| B10 | AI explanation | Detail insiden → Generate | Panel AI; `model_used` badge | | Groq atau `fallback-static` |
| B11 | Live Traffic proof | Setelah B4: baris **Attack 200** lalu **Blocked 403** | Dua fase terlihat | | Lihat GUIDE |
| B12 | 429 rate limit | Setelah B5: refresh vuln-web 10+×/menit | Halaman kuning **429** | | Opsional kuat |

---

## C — Burp Suite

Target: `http://localhost:5050` · UA browser normal untuk tes non-scanner.

### C0 — Setup

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C0.1 | Proxy ON, traffic ke vuln-web | History terisi | | |
| C0.2 | UA bukan default Burp scanner | Tidak auto SCANNER saat SQLi/XSS | | |

### C1 — Brute Force (Intruder)

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C1.1 | POST login 1× salah | Entry history | | |
| C1.2 | Intruder password, 15 payload | ≥10 hit <60 s | | |
| C1.3 | SOC Incidents | **BRUTE_FORCE** high | | |
| C1.4 | Request lanjutan | Bisa **403** | | |

### C2 — SQLi (Repeater)

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C2.1 | POST body `username=admin' OR '1'='1' --&password=x` | Login reflected | | |
| C2.2 | SOC | **SQL_INJECTION** critical | | |
| C2.3 | GET `/` | **403** SME-Guard | | |

### C3 — XSS

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C3.1 | Unblock IP | OK | | |
| C3.2 | `GET /search?q=<script>alert(1)</script>` | Reflected | | |
| C3.3 | SOC | **XSS** critical | | |

### C4 — Path traversal

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C4.1 | `GET /files?file=../../etc/passwd` | Files page | | |
| C4.2 | SOC | **PATH_TRAVERSAL** high | | |

### C5 — Command injection

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C5.1 | `GET /cmd?cmd=;whoami` | Output di halaman | | |
| C5.2 | SOC | **COMMAND_INJECTION** → **403** | | |

### C6 — Scanner & 429

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C6.1 | UA `Nikto/2.1.6` | 200 pertama | | |
| C6.2 | SOC | **SCANNER** medium, Rate Limited tab | | |
| C6.3 | Banyak request cepat | **429** | | |

### C7 — LFI/RFI

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C7.1 | `GET /files?file=php://filter/convert.base64-encode/resource=index` | Logged | | |
| C7.2 | SOC | **LFI_RFI** critical | | |

### C8 — Bukti

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| C8.1 | Screenshot Incidents + IP Mgmt + Live Traffic | Arsip sidang | | |
| C8.2 | Export Burp item / Repeater | Bukti request | | |

---

## D — Setup DOCKER

| # | Langkah | Expected | Pass | Catatan |
|---|---------|-----------------|------|---------|
| D1 | Port 3000/5000/5050/5432 bebas | Tidak bentrok | | |
| D2 | Docker Desktop running | Engine OK | | |
| D3 | `docker compose up --build -d` | 6 service up | | |
| D4 | `docker compose ps` | Semua **running** | | |
| D5 | `docker compose logs backend` | DB ready, log monitor, gunicorn | | |
| D6 | `http://localhost:3000` login | OK | | |
| D7 | `http://localhost:5050` | Shop 200 | | |
| D8 | `GET /api/dashboard/stats` + Bearer | JSON (bukan 502) | | |
| D9 | Setelah ubah kode: `docker compose up --build -d` | Image terbaru | | Mei 2026 features |

---

## E — Serangan DOCKER

Ulangi subset **B** — expected **identik**.

| # | Tes | Ref B | Pass | Catatan |
|---|-----|-------|------|---------|
| E1 | SQLi login | B1 | | |
| E2 | XSS | B2 | | |
| E3 | Brute force | B6 | | |
| E4 | Scanner + 429 | B5, B12 | | |
| E5 | Command injection | B4 | | |
| E6 | Logs backend `[THREAT]` | — | | |
| E7 | Blocked UI = vuln-web 403 | B7 | | |
| E8 | Volume `vuln_logs` sinkron | — | | `blocked_ips.json` shared |

---

## F — Fitur SOC

| # | Fitur | Langkah | Expected | Pass | Catatan |
|---|-------|---------|----------|------|---------|
| F1 | Dashboard | `/` | KPI, timeline, severity chart | | |
| F2 | Chart seed | `seed_chart_demo.py` + refresh | Timeline 7 hari | | |
| F3 | Live Traffic | `/traffic` | Auto-refresh; hide static | | |
| F4 | Detection Rules | `/rules` | CRUD; toggle active; sandbox Test | | |
| F4a | Info icon ⓘ | Hover di samping Add Rule | Tooltip baseline / lab mode | | |
| F5 | Bulk resolve | Select incidents → resolved | Status + audit log | | |
| F6 | Export CSV | Incidents export | File unduh | | |
| F7 | Chatbot | Buka chat, tanya regex/SQLi | Balasan Groq | | Draggable — [J](#j--uiux--mei-2026) |
| F7b | IP Management | Blocked + Rate Limited tabs | Unblock, extend, clear | | |
| F8 | i18n | Settings → EN / ID | Label berubah | | |
| F9 | Theme | Dark / light | Tema berubah | | |
| F10 | Session timeout | Idle lama | Warning logout | | Jika dikonfigurasi |
| F11 | IP History drawer | Klik IP di insiden | Riwayat + pattern | | |
| F12 | Assign analyst | Admin assign di detail | Tersimpan | | |
| F13 | Investigation notes | Add note | Timestamp + user | | |
| F14 | Audit log | `/audit` (admin) | Login, rule, block tercatat | | |
| F15 | Notification bell | Trigger insiden baru | Toast singkat + badge count | | Bukan email |

---

## G — Shop, upload, Fase 3

Unblock IP + reset opsional sebelum mulai.

| # | Fitur | Langkah | Expected | Pass | Catatan |
|---|-------|---------|----------|------|---------|
| G1 | Upload aman | POST `/files` `notes.txt` | Live Traffic normal; **no** FILE_UPLOAD incident | | |
| G2 | Upload berbahaya | `shell.php` di `/files` atau avatar profile | **FILE_UPLOAD** high | | |
| G3 | Path absolut | `?file=E:/.../blocked_ips.json` atau Docker `/app/logs/...` | Baca file + **PATH_TRAVERSAL** | | [DETECTION.md](DETECTION.md) § Security Lab |
| G4 | File aman | `?file=readme.txt` | Konten; no incident | | |
| G5 | Cart | Catalog → Add to cart | Cart page OK | | |
| G6 | Fase 3 CMD | `VULN_UNSAFE_CMD=1` + restart vuln-web | Banner merah; shell nyata; insiden CMD | | |
| G6b | Baca file rahasia | `/cmd?cmd=cat lab_secrets/capstone_flag.txt` (rule CMD off, unblock) | Teks flag di output; **tanpa** butuh `ping` | | Slim Docker: `ping` not found = normal |
| G7 | Fase 3 upload | `VULN_UNSAFE_UPLOAD=1` (opsional) | Path escape upload | | Lab only |
| G8 | Seed rules | Restart backend / cek `/rules` | FILE_UPLOAD + path rules ada | | |

---

## H — Settings & integrasi

| # | Fitur | Langkah | Expected | Pass | Catatan |
|---|-------|---------|----------|------|---------|
| H1 | Save thresholds | Brute 10 → 15, Save, 15× login gagal | BF di hit ke-15 (±60 s) | | |
| H2 | Temp block hours | Ubah jam, Save, trigger high attack | Expire sesuai setting | | |
| H3 | Groq API key | Isi key + model, Save | Configured badge | | |
| H4 | Test Groq | Test Connection | Sukses + nama **model** di pesan | | Satu model terpilih |
| H5 | AI explanation model | Generate pada insiden | Badge = model yang dipakai | | Tooltip di chip |
| H6 | AbuseIPDB | Test API key | Score 8.8.8.8 | | Opsional |
| H7 | Email test | Send test email | Terkirim atau error jelas | | Opsional |
| H8 | Telegram test | Send test message | OK | | Opsional |
| H9 | Alert sound | Toggle + test sound | Bunyi (browser allow) | | Sidebar bell |
| H10 | Lab mode OFF default | Fresh install / reset settings | Detection Rules ⓘ = production text | | |

---

## I — Lab mode & rule kustom

Demo sidang: **rule operator** vs **baseline**.

| # | Langkah | Expected | Pass | Catatan |
|---|---------|----------|------|---------|
| I1 | Settings → Lab mode **ON** → Save | Rules page ⓘ = lab warning | | |
| I2 | Matikan **semua** rule COMMAND_INJECTION | 0 active CMD rules | | |
| I3 | Unblock IP | vuln-web OK | | |
| I4 | `cmd=;whoami` | **No** incident (lab, no baseline) | | Bukti bypass terkontrol |
| I5 | Buat rule: SQLi `(?i)lorem\s+ipsum`, active | Rule di tabel | | |
| I6 | POST login `username=lorem ipsum` | **SQL_INJECTION**; `match_count++` | | |
| I7 | Lab mode **OFF** → Save | ⓘ = production; baseline aktif lagi | | |
| I8 | `cmd=;whoami` lagi | Incident CMD meski rule CMD off | | Baseline OWASP |
| I9 | Sandbox Test payload | Match sesuai engine (lab on/off) | | `/api/detection/test` |

---

## J — UI/UX Mei 2026

| # | Fitur | Langkah | Expected | Pass | Catatan |
|---|-------|---------|----------|------|---------|
| J1 | Create Rule dialog | Add Rule → form | Label **Rule Name** tidak terpotong | | |
| J2 | Chatbot position | Default kanan bawah | Tidak tutup Logout sidebar | | |
| J3 | Chatbot drag | Seret FAB ke pojok lain | Posisi tersimpan setelah refresh | | `localStorage` |
| J4 | Toast insiden | Insiden baru | Toast kanan atas ~2,5 s, max 3 | | |
| J5 | Rate limit chip | IP Management → Rate Limited | Tooltip jika "JSON only" | | Enforcement tetap jalan |

---

## Ringkasan penilaian

| Bagian | Item (≈) | Lulus | Gagal | N/A |
|--------|----------|-------|-------|-----|
| P — Persiapan | 6 | | | |
| A — Setup manual | 7 | | | |
| B — Serangan manual | 12 | | | |
| C — Burp | 20+ | | | |
| D — Docker setup | 9 | | | |
| E — Serangan Docker | 8 | | | |
| F — Fitur SOC | 15 | | | |
| G — Revisi shop/lab | 8 | | | |
| H — Settings | 10 | | | |
| I — Lab mode | 9 | | | |
| J — UI/UX | 5 | | | |

**Total perkiraan:** ~100 skenario (centang per baris yang diuji).

### Keputusan

- ☐ **LULUS** — Manual **dan** Docker; fitur F–J OK; siap sidang
- ☐ **LULUS BERSYARAT** — Catatan: _______________
- ☐ **BELUM LULUS** — Bloker: _______________

### Bloker umum

| Gejala | Solusi |
|--------|--------|
| Insiden tidak muncul | `USE_SIMULATED_LOGS=false`; path log; `docker compose restart backend` |
| Attack 200, tidak 403 | Cek **Incidents**; unblock IP salah; tunggu tailer |
| Rule OFF masih detect | Lab mode OFF → baseline aktif — jelaskan di sidang |
| Lab mode ON masih detect | Rule lain aktif atau brute-force rule aktif |
| Semua request SCANNER (Burp) | UA browser normal |
| 403 terus | IP Management unblock atau `reset_smeguard.py --clear-logs` |
| Threshold Settings tidak jalan | **Save** Settings; tunggu ≤60 s atau restart backend |
| Model AI selalu sama | Normal jika Groq primary sukses; cek tooltip `model_used` |
| Docker backend loop | `docker compose logs backend` — cek `DATABASE_URL` |
| Frontend build gagal | `docker compose build --no-cache frontend` |

### Lampiran — Status Mei 2026

| Item | Status |
|------|--------|
| Core SOC + 8 attack types | Done |
| IP Management Blocked + Rate Limited | Done |
| Lab mode UI-only detection | Done |
| OWASP baseline + rule UI (production) | Done |
| AI Groq + static fallback | Done |
| vuln-web shop + Fase 3 | Done |
| Dokumentasi Form 4 | Tim |
| **Audit full Mei 2026** | Dokumen ini |

**Deploy / Git:** [additional/DEPLOY.md](additional/DEPLOY.md) · [additional/GITHUB.md](additional/GITHUB.md)

---

*Audit Full SME-Guard — Mei 2026 · President University Capstone*
