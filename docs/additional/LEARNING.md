# Incidentra — Materi belajar

Konsep untuk capstone / sidang. Guide: [../GUIDE.md](../GUIDE.md) · Arsitektur: [../ARCHITECTURE.md](../ARCHITECTURE.md) · Audit: [../AUDIT.md](../AUDIT.md)

---

## 1. Apa itu “token login”?

**JWT** dikirim setelah login benar. Setiap request API membawa header:

`Authorization: Bearer <token>`

Tanpa token → `{ "error": "Authorization required" }` — itu normal, bukan bug.

### Alur

```
:3000 login → POST /api/auth/login → token
→ localStorage incidentra_token
→ axios menambah Bearer pada setiap /api/*
```

| Bagian | File |
|--------|------|
| Login | `backend/app/api/auth.py` |
| Verifikasi | `backend/app/api/auth_middleware.py` |
| Kirim token | `frontend/src/services/api.js` |

---

## 2. Kenapa buka URL API langsung di browser gagal?

`http://localhost:5000/api/dashboard/stats` di address bar = GET tanpa header Authorization.

Dashboard `:3000` memanggil API lewat JavaScript **dengan** token. Jika grafik tampil setelah login → token OK.

---

## 3. Verifikasi token (opsional)

**UI:** Login → Dashboard grafik OK → log backend `GET .../stats 200`.

**PowerShell:**

```powershell
$body = '{"username":"admin","password":"Admin@Incidentra2026!"}'
$r = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" -Method POST -Body $body -ContentType "application/json"
Invoke-RestMethod -Uri "http://localhost:5000/api/dashboard/stats" -Headers @{ Authorization = "Bearer $($r.token)" }
```

---

## 4. Admin vs analyst

JWT berisi `role`. Bulk resolve & audit = admin saja. Detail: [../ARCHITECTURE.md](../ARCHITECTURE.md).

---

## 5. Log → insiden → respons

```
Request vuln-web → access.log → DetectionEngine → Incident (PostgreSQL)
→ ResponseManager → blocked_ips (DB) + JSON + Redis
→ vuln-web baca JSON → 403 / 429
```

Severity → respons: [AUDIT.md](../AUDIT.md) (tabel awal).

---

## 6. Database, JSON, dan Bab capstone

### Apakah rate limit “kurang” karena tidak di DB?

**Tidak untuk scope Bab 3–4.** Dari awal desain Incidentra:

| Data | Penyimpanan | Alasan |
|------|-------------|--------|
| Insiden, user, rules, audit | **PostgreSQL** | Laporan, histori, query SOC |
| Blokir IP (metadata) | **PostgreSQL** + salinan JSON | UI + enforcement vuln-web |
| Rate limit aktif | **JSON + Redis** | Kebijakan sementara; vuln-web tidak pakai DB |
| Log mentah | **File** | Terlalu besar; dipantau streaming |

Ini **arsitektur hybrid** — umum di SOC kecil: DB untuk “record of truth”, file ringan untuk edge enforcement.

### Apakah pernah ditambah tabel saat revisi?

Skema memakai **`db.create_all()`** (tanpa folder migrasi Alembic). Revisi menambah **fitur di tabel yang sudah ada** (mis. kolom threat intel di `incidents`, `audit_logs`, `app_settings`) dan **API baru** (`/api/rate-limited/`), bukan tabel `rate_limited_ips`.

Itu **konsisten** dengan Bab 3 yang menyatakan rate limit di Redis/JSON.

### Perasaan “selalu ada yang kurang” di Bab 4

Normal dalam capstone. Cara mengelolanya:

1. **Freeze scope sidang** — daftar “wajib demo” (lihat [AUDIT.md](../AUDIT.md)); sisanya backlog.
2. **Dokumentasikan keputusan** — mis. “Rate limit tidak di DB karena …” (1 paragraf di laporan Bab 4).
3. **Jangan chase perfection** — IP Management + Docker + audit manual/Burp sudah di atas rata-rata untuk UKM SOC lab.
4. **Backlog eksplisit** di laporan: notification bell, korelasi insiden, migrasi Alembic — bukan “lupa”, tapi “future work”.

**Yang sudah selesai (Mei 2026) vs rencana lama:**

| Rencana lama | Status |
|--------------|--------|
| Edit durasi blokir UI | ✅ |
| Kelola rate limit UI | ✅ |
| Docker end-to-end | ✅ |
| PATH_TRAVERSAL vs LFI tie-break | ✅ |

### Kapan perlu tambah tabel DB?

Hanya jika dosen **mensyaratkan** “semua state enforcement di PostgreSQL”. Kalau ya: tabel `rate_limited_ips` + tetap sync ke JSON untuk vuln-web. Untuk sidang saat ini, **dokumentasi hybrid lebih kuat** daripada migrasi besar menjelang deadline.

---

## 7. Env Docker vs manual

| | Manual | Docker |
|---|--------|--------|
| File | `backend/.env` | `.env.docker` + `docker-compose.yml` |
| DB host | `localhost` | `postgres` (service name) |
| Frontend API | proxy / `.env` | build arg `REACT_APP_API_URL` |

Detail: [GITHUB.md](GITHUB.md).

---

*Materi belajar Incidentra — tim capstone President University.*
