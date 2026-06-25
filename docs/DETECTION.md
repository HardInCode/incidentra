# Incidentra — Detection & Security Lab

Maps **where detection code lives**, distinguishes **AI analyst** vs **OWASP baseline**, and summarizes **vuln-web Phase 3** lab scenarios. Use at defense demo or when examiners ask Ctrl+F questions.

**Audit:** [AUDIT.md](AUDIT.md) · **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Guide:** [GUIDE.md](GUIDE.md)

---

## Dua hal berbeda (jangan disamakan)

| Lapisan | Fungsi | File utama |
|---------|--------|------------|
| **Deteksi insiden** | Regex + brute-force → insiden + blok IP | `backend/app/core/detection_engine.py` |
| **AI analyst** | Penjelasan insiden untuk manusia (Groq) | `backend/app/services/ai_service.py` |

**AI fallback** = jika Groq gagal → teks statis `fallback-static` (bukan deteksi serangan).

**OWASP baseline** = regex bawaan di `DETECTION_PATTERNS` (bukan AI). Default **selalu digabung** dengan rule dari UI.

---

**Code comments index (sidang Ctrl+F):** search `SIDANG Ctrl+F` in `backend/app/core/`, `backend/app/api/traffic.py`, `vuln-web/middleware/security.py`, `frontend/src/pages/Incidents.js`, `IPHistoryDrawer.js`.

## Ctrl+F — lokasi kode

| Cari string ini | Arti |
|-----------------|------|
| `OWASP_BASELINE_PATTERNS` | Komentar penanda di `detection_engine.py` |
| `DETECTION_PATTERNS` | Dict pola bawaan (SQLi, XSS, CMD, …) |
| `_load_rules_from_db` | Muat rule aktif dari PostgreSQL |
| `is_lab_mode_ui_only` | Mode lab: hanya rule UI |
| `DetectionEngine.analyze` | Entry point deteksi per baris log |
| `BruteForceTracker` | Brute force (threshold) |
| `RESPONSE_ACTIONS` | Severity → monitor / rate_limit / escalating_block |
| `enforce_security` | vuln-web baca `blocked_ips.json` → 403 |
| `_call_groq_with_fallback` | Rantai model Groq untuk penjelasan AI |
| `DETECTION_LAB_MODE_UI_ONLY` | Setting di Settings (DB) |

---

## Alur singkat

```
vuln-web → access.log → log_monitor → parse_log_line → DetectionEngine.analyze()
    → Incident (PostgreSQL) → ResponseManager → blocked_ips.json / rate_limited.json
    → vuln-web 403/429 pada request berikutnya
```

Opsional (async): `ai_service` → `IncidentExplanation` (tidak mempengaruhi blokir).

---

## Mode Lab (Settings)

| Setting | Default | Efek |
|---------|---------|------|
| **Lab mode OFF** | Ya (produksi/demo umum) | Rule UI **+** baseline `DETECTION_PATTERNS` |
| **Lab mode ON** | Tidak | Hanya rule **aktif** di Detection Rules; baseline OWASP **mati**; brute force hanya jika ada rule BRUTE_FORCE aktif |

**Docker:** tidak perlu rebuild image; simpan Settings → backend terapkan dalam ±60 detik (atau restart `backend` untuk langsung).

**Demo sidang (custom rule):**

1. Settings → aktifkan **Lab mode** → Save.
2. Detection Rules → buat rule SQLi mis. `(?i)lorem\s+ipsum` → aktif.
3. Unblock IP di IP Management.
4. POST `/login` dengan `username=lorem ipsum` → insiden dari **rule Anda**.
5. Matikan rule / lab mode → perilaku kembali ke baseline (jika rule OFF saja masih ada baseline kecuali lab ON).

---

## Detection Thresholds (Settings)

| Field | Dipakai di |
|-------|------------|
| Brute Force Threshold | `BruteForceTracker` — POST gagal ke `/login` |
| Rate Limit Window | Jendela brute force + policy rate limit |
| Repeat Offender Threshold | Jumlah offense sebelum badge **Repeat Offender** |
| Escalating High Durations | Durasi blok per offense tier (High): default `1, 24, 168` jam |
| Escalating Critical Durations | Durasi blok per offense tier (Critical): default `24, 168, 720` jam |
| Temp Block Duration | Legacy/manual temporary block (jam × 3600 → detik) |

Nilai dibaca dari **AppSetting** (setelah Save) lalu env `.env` sebagai fallback.

---

## HTTP 429 di vuln-web

Muncul ketika IP ada di `rate_limited.json` **dan** melebihi `max_requests` dalam `window_seconds` (default 10 req / 60 s).

Typical trigger: insiden **SCANNER** (severity medium) → `rate_limit`, bukan permanent block.

---

## Rate Limited tab — "Listed in rate_limited.json only"

Artinya IP tercatat di file JSON enforcement, tetapi kunci Redis `ratelimit:{ip}` tidak punya TTL (Redis restart, worker baru, atau Redis down). **vuln-web tetap rate-limit** memakai JSON + hitungan request di middleware.

---

## Live Traffic vs insiden

| | Live Traffic | Incidents |
|--|--------------|-----------|
| File | `backend/app/api/traffic.py` | `detection_engine.py` |
| Tag Attack | Keyword ringan | — |
| Insiden | — | Regex penuh + brute force |

SQLi bisa tag **Normal** di Live Traffic tetapi tetap jadi insiden jika pola engine match.

---

---

## Security Lab (vuln-web Phase 3)

**Docker Compose (default in repo):** `VULN_UNSAFE_CMD=1` and `VULN_UNSAFE_UPLOAD=1` on service `vuln_web` — red banner on shop pages; real shell on `/cmd`; upload path escape when upload flag is on.

| Flag | Effect |
|------|--------|
| `VULN_UNSAFE_CMD=1` | `/cmd?cmd=...` runs `subprocess` (timeout 5s) |
| `VULN_UNSAFE_UPLOAD=1` | POST `/files` may write outside `safe_files/uploads/` |

**Whitelist IP:** `BlockedIP.is_whitelist=True` → excluded from `blocked_ips.json`; `DetectionEngine.analyze` returns `None` for that IP (no new incidents).

## Escalating Block Policy (Mei–Juni 2026)

| Severity | Auto action | Default durasi (offense 1 → 2 → 3+) |
|----------|-------------|-------------------------------------|
| low | log & monitor | — |
| medium | rate limit | — |
| high | `escalating_block` | 1h → 24h → 7d |
| critical | `escalating_block` | 24h → 7d → 30d |

- **Tidak ada permanent auto-block** untuk insiden otomatis — permanent hanya via **manual block** di IP Management.
- Offense ke-3+ (default threshold) → badge **Repeat Offender** (`is_repeat_offender=True`).
- Unblock IP **tidak** reset counter eskalasi — disimpan di Redis (`escalation_count:{ip}`) selama 30 hari.
- Severity tertinggi pernah tercatat menentukan daftar durasi (critical list menang atas high).

**PATH_TRAVERSAL / FILE_UPLOAD / BRUTE_FORCE:** severity **high** → escalating block (bukan permanent). **SQL_INJECTION / XSS / COMMAND_INJECTION / LFI_RFI:** severity **critical** → escalating block (offense #1 default 24 jam, bukan permanent).

**Absolute path on `/files`:** `?file=E:/.../blocked_ips.json` or `/app/logs/...` may read files without `../` — may not match classic traversal regex; optional custom rule: `blocked_ips\.json`, `[/\\]logs[/\\]`.

**Demo flag file (Docker slim):** `cmd=cat lab_secrets/capstone_flag.txt` works; `ping` often missing in image — not a detection failure.

Full lab payloads and bypass notes: see [GUIDE.md](GUIDE.md) Phase 3 section and [AUDIT.md](AUDIT.md) section G.

---

*Incidentra — Detection & Security Lab, June 2026.*
