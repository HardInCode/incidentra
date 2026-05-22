# Prompt handoff — perbaikan bug & inkonsistensi SME-Guard (Mei 2026)

**Copy-paste blok di bawah ke chat Cursor baru.** Jangan perbaiki di sesi ini kecuali user minta — dokumen ini hanya konteks.

---

## Prompt untuk chat baru

```
Kamu memperbaiki SME-Guard (Incidentra) di repo E:/Capstone/May/sme-guard-May.
Stack: Flask backend, React SOC, vuln-web Flask, Docker Compose, PostgreSQL, Redis.

User menemukan bug/inkonsistensi SEBELUM audit penuh. Perbaiki semua item di bawah.
Jangan ubah scope capstone berlebihan — fokus bug + UX + dokumentasi singkat.

### Konteks arsitektur (wajib baca)

1. **Deteksi insiden:** log_monitor → parse_log_line → DetectionEngine.analyze → Incident → ResponseManager.respond
   - File: backend/app/core/log_monitor.py, detection_engine.py, response_manager.py
   - Baseline OWASP: DETECTION_PATTERNS (kecuali Settings Lab mode ON = UI rules only)
   - Settings: backend/app/core/settings_reader.py, DETECTION_LAB_MODE_UI_ONLY

2. **Enforcement vuln-web:** blocked_ips.json + rate_limited.json (bukan DB langsung)
   - vuln-web/middleware/security.py → 403 / 429

3. **Live Traffic ≠ deteksi:** backend/app/api/traffic.py pakai ATTACK_KEYWORDS ringan
   - Tag Attack/Normal TIDAK sama dengan engine / insiden

4. **Severity → action:** RESPONSE_ACTIONS di detection_engine.py
   - PATH_TRAVERSAL = **high** → temporary_block (~24h), BUKAN permanent
   - SQL_INJECTION = **critical** → permanent_block
   - SCANNER = **medium** → rate_limit (429, bukan 403 permanen)

5. **Aturan demo:** Request pertama serangan sering **HTTP 200** + tag Attack di Live Traffic;
   blokir **403** biasanya request **berikutnya** setelah insiden + JSON ter-update.

### Bug / issue yang dilaporkan user

#### 1) Export CSV — Ongoing vs All Incidents harus beda

**Gejala:** Export dari `/incidents` (ongoing) dan `/incidents/all` terasa sama / file sama.

**Temuan kode:**
- frontend/src/pages/Incidents.js `handleExportCsv` memang kirim `buildStatusQuery(mode, status)`:
  - ongoing → `status_in=new,investigating` (kecuali filter status spesifik)
  - all → semua status (atau filter status user)
- Backend incidents.py `/export` pakai `_apply_incident_filters` — OK secara data
- **Masalah UX:** `a.download = 'incidents.csv'` SELALU sama untuk kedua halaman
- Export dialog tidak menampilkan mode (ongoing vs all) di hint/filename

**Harapan perbaikan:**
- Nama file berbeda: mis. `incidents-ongoing.csv` vs `incidents-all.csv`
- Hint export menjelaskan scope per halaman
- Opsional: default date range berbeda; tes manual bahwa row resolved hanya ada di export all

#### 2) Tombol Whitelist di IP History Drawer — bug + fungsi tidak jelas

**Gejala:** Tombol Whitelist di drawer error / membingungkan.

**Fungsi yang SEHARUSNYA (desain SME-Guard):**
- Admin menandai IP **dipercaya** → entri `BlockedIP` dengan `is_whitelist=True`
- IP whitelist **tidak** masuk `blocked_ips.json` (response_manager._write_blocked_ips_json filter is_whitelist=False)
- Tampil di IP History sebagai status "Whitelisted"

**Temuan kode (kemungkinan bug):**
- frontend/src/components/shared/IPHistoryDrawer.js `handleWhitelist`:
  POST `/api/blocked-ips/` dengan is_whitelist=true
- backend/app/api/blocked_ips.py: jika IP **sudah ada** di tabel (dari block/rate limit sebelumnya) → **409 IP already in list**
- **Gap:** Detection engine TIDAK skip IP whitelist saat analyze — whitelist hanya affect JSON block list, bukan stop insiden
- Whitelist pakai `block_type: 'permanent'` + `is_whitelist: true` — semantik aneh

**Harapan perbaikan:**
- Whitelist harus work jika IP sudah pernah di-block/rate-limited (update row atau endpoint khusus PATCH whitelist)
- UI copy: jelaskan "IP dipercaya, tidak auto-block di vuln-web"
- Putuskan: apakah deteksi juga harus skip IP whitelist? (product decision — dokumentasikan)
- Tes: IP 172.19.0.1 (Docker) setelah whitelist tidak 403 dari SOC

#### 3) Path traversal — terdeteksi di Live Traffic (Attack 200) tapi IP tidak ter-block

**Lingkungan user:** Docker, Phase 3 ON (VULN_UNSAFE_CMD=1, VULN_UNSAFE_UPLOAD=1).
Payload: `GET /files?file=../../etc/passwd`
Sudah dicoba Lab mode (rule PATH_TRAVERSAL ada) dan baseline ON — tetap 200, tidak 403.

**Temuan kode:**
- vuln-web/routes/files.py: `../` di-strip di path relatif; tetap log URL penuh di access.log → traffic tag Attack (`../` di ATTACK_KEYWORDS)
- Engine: pola `../` di DETECTION_PATTERNS → PATH_TRAVERSAL severity **high** → temporary_block, bukan permanent
- **Cek saat perbaikan:**
  - Apakah insiden PATH_TRAVERSAL benar-benar muncul di tab Incidents?
  - Apakah `blocked_ips.json` di volume Docker ter-update? (vuln_logs)
  - Apakah IP sudah whitelisted / waiver unblock / dedup 5 menit?
  - Apakah user hanya lihat request PERTAMA (200 normal sebelum block)?
  - Backend logs: `[THREAT] PATH_TRAVERSAL`?

**Harapan perbaikan:**
- Jika insiden tidak terbuat → fix detection/rule/lab mode
- Jika insiden terbuat tapi tidak 403 → fix JSON path Docker / respond()
- UX: jelaskan PATH_TRAVERSAL = temporary block; atau naikkan ke critical jika product minta parity dengan SQLi (diskusikan dampak audit)
- Dokumentasi TUTORIAL/AUDIT: first hit 200, second hit 403

#### 4) SQLi — Live Traffic Normal tapi IP ter-block (inkonsistensi tag)

**Gejala:** Payload jelas SQLi, status 200, tag **Normal** di Live Traffic, tapi IP tetap masuk blocked & 403.

**Root cause (sudah diketahui):**
- traffic.py ATTACK_KEYWORDS: `'or 1=1'` — payload user `admin' OR '1'='1' --` tidak match (spasi, quote)
- detection_engine regex lengkap → insiden SQL_INJECTION + permanent block

**Harapan perbaikan:**
- Selaraskan Live Traffic tagging dengan engine (subset pattern) ATAU
- Label UI: "Heuristic tag — verify in Incidents" + warna berbeda
- Tambah keyword/pattern untuk POST login SQLi umum di traffic.py
- Jangan pecah pipeline — tetap dua lapisan tapi jujur di UI/docs

### Audit tambahan yang diminta user (cari masalah serupa)

Scan dan catat (boleh perbaiki dalam PR yang sama jika kecil):

| Area | Pertanyaan |
|------|------------|
| Export vs list filter | Apakah semua filter (search, severity, attack type) konsisten list vs export? |
| IP History Block button | Apakah sama 409 jika IP sudah ada? |
| Rate limit vs Blocked | User lihat "Listed in rate_limited.json only" — sudah normal jika Redis TTL kosong; pastikan 429 masih jalan |
| Critical vs high | User ekspektasi semua serangan = 403 permanen; dokumentasi severity table |
| Lab mode + rule OFF | Apakah masih ada insiden dari brute force builtin? |
| Dedup 5 menit | Apakah user mengira "tidak block" karena insiden kedua di-skip? |
| Simulate / inject log | Apakah selaras dengan detection? |
| i18n EN/ID | String baru untuk fix |

### File kunci (Ctrl+F)

- CODE-COMMENTS-MAP.md, DETECTION-GUIDE.md
- frontend: Incidents.js, IPHistoryDrawer.js, traffic (backend)
- backend: incidents.py (export), blocked_ips.py, ip_history.py, traffic.py, log_monitor.py

### Docker tes setelah fix

```powershell
docker compose up --build -d
# Reset: scripts/reset_smeguard + clear blocked_ips.json di volume
```

Tes minimal:
1. SQLi login → insiden + Normal/Attack di traffic (setelah fix tag) + 403 request berikutnya
2. Path traversal → insiden PATH_TRAVERSAL + 403 request berikutnya
3. Export ongoing vs all → file & row count berbeda
4. Whitelist IP Docker → sukses + perilaku jelas

### Deliverable

- Fix kode minimal + tes manual singkat
- Update 1-2 kalimat di TUTORIAL atau DETECTION-GUIDE jika perilaku berubah
- Jangan rewrite Form 4 kecuali user minta
- Commit hanya jika user minta
```

---

## Jawaban singkat untuk pertanyaan user (bukan bagian prompt)

### Rate limit — "Listed in rate_limited.json only" normal?

**Ya, normal** di setup Anda: IP ada di `rate_limited.json`, tapi kunci Redis `ratelimit:{ip}` tidak punya TTL (restart worker / Redis kosong). **vuln-web tetap bisa 429** lewat hitungan request di middleware + file JSON. Bukan berarti rate limit "mati".

### Path traversal tidak block — kemungkinan besar

1. **Bukan bug toggle** — cek dulu apakah ada **insiden** PATH_TRAVERSAL di SOC.
2. **High = blokir sementara**, bukan seperti SQLi (critical) — tetap harus **403 pada request berikutnya**.
3. Request **pertama** memang sering **200** (termasuk tag Attack di traffic).
4. Jika **tidak ada insiden** → masalah deteksi/config; jika **ada insiden tapi 200 terus** → JSON enforcement / IP salah / whitelist.

### SQLi Normal di traffic tapi IP block

**Konsisten dengan kode saat ini** — engine deteksi, traffic hanya keyword kasar. Item #4 di prompt di atas.

---

*Handoff prompt — generated for new Cursor session, Mei 2026.*
