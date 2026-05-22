# Prompt — Revisi dokumentasi SME-Guard (percakapan baru)

**Cara pakai:** Copy seluruh blok di bawah (antara garis `---`) ke chat Cursor **baru**. Jangan jalankan revisi di sesi lama.

---

```
Kamu merevisi folder dokumentasi proyek capstone SME-Guard (Incidentra) di:
E:/Capstone/May/sme-guard-May

## Tujuan utama

1. **Kurangi kebingungan** — docs terlalu banyak dan tumpang tindih; gabungkan yang bisa digabung, hapus yang tidak perlu.
2. **Selaraskan dengan aplikasi versi terbaru (Mei 2026)** — baca kode aktual (`README.md`, `docker-compose.yml`, `frontend/src/App.js`, `backend/app/`) sebelum menulis; jangan mengandalkan memori lama.
3. **Form 4 Implementation** — buat **versi baru** untuk dibandingkan dengan yang lama; **jangan hapus** `docs/form4/FORM4_IMPLEMENTATION.md` (arsip/compare).

## Status user (penting)

- User sudah mengerjakan **Word/docx Form 4** dan sudah sampai **Bagian B (Product Display)** dengan screenshot **sangat lengkap** (termasuk notifikasi, pop-up, error, dll.) di Word — **pertahankan/rujuk ke Word untuk B**, jangan duplikasi massal screenshot di markdown kecuali checklist.
- `FORM4_IMPLEMENTATION.md` saat ini **kurang lengkap vs template kampus** dan vs app terbaru (contoh: tab **All Incidents** `/incidents/all`, export CSV terpisah ongoing vs all, IP History whitelist, Lab mode, Phase 3, perbaikan Mei 2026).
- User minta output Form 4 mengikuti struktur template resmi di bawah.

---

## Template kampus — PART 4 IMPLEMENTATION (wajib dipenuhi)

### A. DESIGNS IMPLEMENTATION
1. Functions/Procedure/Class — **jelaskan dengan cuplikan kode** (bukan hanya paragraf); map ke Form 3 Part B per subsistem.
2. Database implementation — tabel, kolom, dual-write JSON, apa yang TIDAK di DB (rate limit).
3. User Interface implementation — semua halaman/route SOC + vuln-web.
4. Hardware implementation — N/A (software only) + spesifikasi minimum.
5. Integration — alur modul + diagram.

### B. PRODUCT DISPLAY
1. Software — deskripsi tiap komponen + screenshot semua skenario (error, pop-up, notifikasi, 403/429, dll.).
2. Hardware — N/A atau IoT jika ada.

### C. COMPONENT COST ANALYSIS
Tabel: No | Item | Unit | Price per Unit | Total (+ hosting approximation).

### D. FUNCTIONAL TESTING
**Satu tabel per fitur** (Login, SQLi, XSS, Path Traversal, Block/Unblock, Rate limit, Live Traffic, Rules CRUD, AI, Whitelist, Export CSV, All vs Ongoing incidents, dll.):
No | Scenario | Every Possible Input | Expected Output | Output Result

### E. MANUAL GUIDE
1. System build (developer) — Docker + manual 3-terminal.
2. End-user installation — browser/VPS, tanpa install client.
3. User guide per role — tabel Admin / Analyst / (lab user) + prosedur langkah.

### REFERENCES
Daftar referensi akademis/teknis.

---

## Deliverable yang harus kamu hasilkan

### 1. Struktur docs baru (usulkan lalu eksekusi)

**Target: ~6–8 file inti** (bukan 19+):

| File baru / dipertahankan | Isi |
|---------------------------|-----|
| `docs/README.md` | **Peta docs** — 1 halaman: file apa, untuk siapa, urutan baca |
| `docs/GUIDE.md` | Gabungan: quick start + tutorial sidang + troubleshooting (dari `TUTORIAL.md`) |
| `docs/ARCHITECTURE.md` | Gabungan: `APPLICATION.md` + diagram alur + storage (PG/Redis/JSON/log) |
| `docs/DETECTION.md` | Gabungan: `DETECTION-GUIDE.md` + ringkas `SECURITY-LAB.md` (lab Phase 3) |
| `docs/AUDIT.md` | Satu audit aktif (`AUDIT_FULL_MEI_2026.md`); arsip redirect saja |
| `docs/form4/` | Tetap untuk capstone Word |
| `docs/additional/` | Opsional: GitHub, deploy, learning — atau merge ke GUIDE jika tipis |

**Hapus atau redirect** (setelah merge):
- `docs/Untitled`
- `docs/AUDIT_2026-05-19.md` → 5 baris redirect ke `AUDIT.md`
- `docs/FIX-HANDOFF-PROMPT.md` → hapus setelah bug fix selesai (atau pindah ke `docs/archive/`)
- `docs/CODE-COMMENTS-MAP.md` → pertahankan hanya jika tim masih pakai Ctrl+F sidang; kalau tidak, ringkas jadi 1 section di DETECTION.md
- Duplikasi `additional/PENGUASAAN-APLIKASI.md` vs ARCHITECTURE — merge, hindari 2 narasi arsitektur sama

Update `README.md` (root) tabel dokumentasi agar hanya link ke struktur baru.

### 2. Form 4 — file baru untuk compare

- **KEEP:** `docs/form4/FORM4_IMPLEMENTATION.md` (tidak di-overwrite).
- **CREATE:** `docs/form4/FORM4_IMPLEMENTATION_v2.md` — versi lengkap selaras template A–E + app Mei 2026.
- **CREATE:** `docs/form4/REVISION_LOG.md` — daftar perubahan v1 → v2 (bullet: apa ditambah/diperbaiki/dihapus).
- **UPDATE:** `docs/form4/README.md`, `FORM4_COVER.md`, `FORM4_SCREENSHOTS.md` (checklist wajib termasuk fitur baru).
- **OPTIONAL:** `docs/form4/FORM4_CONTEXT.md` — singkat prompt AI jika masih dipakai.

**Catatan Part B di v2:** Karena user sudah punya screenshot lengkap di Word, di markdown Part B cukup:
- daftar figure + 1–2 kalimat per screen,
- referensi "lihat screenshot di dokumen Word / folder `docs/form4/screenshots/`",
- **jangan** ulang 50+ placeholder `[SCREENSHOT:]` jika user sudah isi Word.

### 3. Gap wajib diisi di v2 (cek di kode, lalu tulis)

Fitur yang **harus** muncul di A.1 / A.3 / D / E (banyak yang kurang atau hanya 1 kalimat di v1):

| Fitur | Bukti di kode |
|-------|----------------|
| **Ongoing Incidents** `/incidents` | `Incidents mode="ongoing"`, filter `status_in=new,investigating` |
| **All Incidents** `/incidents/all` | `Incidents mode="all"`, arsip resolved/false_positive |
| **Export CSV** terpisah | `list_scope=ongoing\|all`, file `incidents-ongoing.csv` vs `incidents-all.csv` |
| **IP History drawer** | `IPHistoryDrawer.js`, API `/api/ip/<ip>/history` |
| **Whitelist IP** | `BlockedIP.is_whitelist`, upsert POST, skip detection, tidak masuk `blocked_ips.json` |
| **Bulk resolve** (admin) | `Incidents.js` selection mode |
| **Chatbot widget** | `ChatbotWidget.js`, `/api/chatbot` |
| **Notification bell** | `NotificationBell.js`, email/Telegram |
| **Session timeout warning** | `SessionTimeoutWarning.js` |
| **Lab mode (Settings)** | `settings_reader.is_lab_mode_ui_only`, UI rules only |
| **Phase 3 lab** | `VULN_UNSAFE_CMD`, `VULN_UNSAFE_UPLOAD` di docker-compose |
| **Live Traffic heuristic** | `traffic.py` — tag Attack ≠ insiden; 200 lalu 403 |
| **PATH_TRAVERSAL = temporary block** | `RESPONSE_ACTIONS` high → bukan permanent |
| **Perbaikan blokir Mei 2026** | `_block_ip` return bool, `is_whitelist=False` on auto-block |

Part A.1: untuk tiap subsistem (log_parser, log_monitor, detection_engine, response_manager, tiap blueprint API, halaman React utama), sertakan **minimal 1 cuplikan kode** (10–25 baris) + penjelasan — sesuai permintaan template "Explain the code for each part".

Part D: tambah tabel terpisah untuk:
- Export CSV (ongoing vs all),
- All Incidents navigation,
- IP History + Whitelist,
- Lab mode,
- Notification (jika dikonfigurasi).

### 4. Gaya penulisan

- Bahasa: **English** untuk isi Form 4 (sesuai docx user); README docs boleh bilingual ringkas (ID) di peta docs saja.
- Nada: formal capstone, passive voice boleh, hindari marketing berlebihan.
- Setiap klaim fitur **harus** bisa diverifikasi path file.
- Jangan commit `.env` atau secrets.

### 5. Workflow eksekusi (urutan)

1. Scan `docs/` + root `README.md` — buat inventaris merge/delete.
2. Baca kode kunci (30 menit): `App.js`, `Incidents.js`, `IPHistoryDrawer.js`, `detection_engine.py`, `response_manager.py`, `incidents.py`, `blocked_ips.py`, `docker-compose.yml`.
3. Tulis `REVISION_LOG.md` (rencana) → user bisa approve implisit dengan lanjut.
4. Buat `FORM4_IMPLEMENTATION_v2.md` lengkap A–E.
5. Merge docs non-form4 → struktur baru; redirect/hapus file lama.
6. Update `docs/form4/README.md` + root README.
7. Di akhir chat: berikan **ringkasan untuk user** — apa yang di-merge, dihapus, apa yang harus copy dari v2 ke Word (bagian A, C, D, E; B tetap dari Word user).

### 6. Yang TIDAK dilakukan

- Tidak mengubah kode aplikasi kecuali user minta (sesi ini **docs only**).
- Tidak meng-overwrite `FORM4_IMPLEMENTATION.md`.
- Tidak membuat commit git kecuali user minta explicitly.

### 7. Referensi internal saat menulis

- Audit skenario: `docs/AUDIT_FULL_MEI_2026.md`
- Handoff bug sudah diperbaiki (Mei 2026): `docs/FIX-HANDOFF-PROMPT.md` — gunakan sebagai daftar perilaku benar, lalu hapus/arsipkan file itu setelah docs sync.

Mulai dengan: **inventaris tabel** (file lama → aksi merge/keep/delete) + **outline FORM4_IMPLEMENTATION_v2.md** per section A–E, lalu implementasi bertahap.
```

---

*File ini hanya prompt starter — bukan hasil revisi.*
