# PEMAHAMAN INCIDENTRA — HULU KE HILIR

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

- [ ] 1. Login & Self-Registration
- [ ] 2. Dashboard (KPI cards, charts, globe)
- [ ] 3. Log Ingestion → Detection (dari access.log sampai jadi Incident)
- [ ] 4. Automated Response (block/rate-limit/escalation)
- [ ] 5. Incident Detail + AI Explanation (Groq)
- [ ] 6. IP Management (Blocked/Rate Limited/Whitelist)
- [ ] 7. Detection Rules CRUD + rules_dirty reload
- [ ] 8. Notifications (Email/Telegram) + AbuseIPDB
- [ ] 9. Settings + User Management (RBAC) + Audit Log
- [ ] 10. Docker Compose — bagaimana 6 service saling terhubung

---

## 1. Login & Self-Registration

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Frontend | `frontend/src/pages/Login.js` | `Ctrl+F` (baris 1) → `handleLogin`, `handleRegister` |
| Frontend | `frontend/src/services/api.js` | `login`, `register` |
| Backend | `backend/app/api/auth.py` | `Ctrl+F` (baris 1) → `login`, `register`, `_make_token`, `_register_rate_limited` |
| Backend | `backend/app/api/auth_middleware.py` | `verify_token` |
| Backend | `backend/app/models/__init__.py` | `class User` |

**Alur (isi sendiri sambil klik-klik):**

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

## 2. Dashboard (KPI cards, charts, globe)

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Frontend | `frontend/src/pages/Dashboard.js` | *(belum ada Ctrl+F anchor — tambahkan kalau perlu)* |
| Frontend | `frontend/src/components/dashboard/AttackOriginsGlobe.js` | *(komponen globe)* |
| Backend | `backend/app/api/dashboard.py` | *(belum ada Ctrl+F anchor)* |

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

---

## 3. Log Ingestion → Detection

**Files terlibat:**

| Layer | File | Ctrl+F anchor |
|---|---|---|
| Backend | `backend/app/core/log_parser.py` | `Ctrl+F` → `parse_log_line`, `LogTailer`, `POST_DATA_PATTERN` |
| Backend | `backend/app/core/log_monitor.py` | `Ctrl+F` → `ingest_log_lines`, `_process_log_line`, `start_monitor` |
| Backend | `backend/app/core/detection_engine.py` | `Ctrl+F` → `OWASP_BASELINE_PATTERNS`, `DETECTION_PATTERNS` |
| Target app | `vuln-web/middleware/logging.py` | *(cara POST_DATA ditulis ke access.log)* |

**Alur:**

1.

**Pemahaman saya:**

-

**Pertanyaan saya:**

- Q1.

**Jawaban:**

- A1.

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
| | | |
