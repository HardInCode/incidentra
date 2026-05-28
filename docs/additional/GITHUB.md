# Incidentra — GitHub & kolaborasi

Repositori resmi: **[https://github.com/HardInCode/incidentra](https://github.com/HardInCode/incidentra)**

---

## Clone pertama kali

```powershell
git clone https://github.com/HardInCode/incidentra.git
cd incidentra
copy backend\.env.docker.example backend\.env.docker
# Opsional: notepad backend\.env.docker  (GROQ_API_KEY — jangan commit file ini)
docker compose up --build -d
```

Manual Windows: ikuti [../GUIDE.md](../GUIDE.md) Opsi B (`backend\.env` dari `.env.example`).

---

## File yang tidak di-push (rahasia / lokal)

| File | Alasan |
|------|--------|
| `backend/.env` | Kredensial manual + DB lokal |
| `backend/.env.docker` | API keys Docker (salin dari `.env.docker.example`) |
| `vuln-web/.env` | Port lokal |
| `frontend/.env` | Override API URL lokal |
| `**/logs/*.log`, `blocked_ips.json`, `rate_limited.json` | State runtime lab |

Yang **aman di repo**: `*.env.example`, `backend/.env.docker.example`, kode, `docs/`, `docker-compose.yml`.

---

## Push perubahan (tim)

```powershell
cd E:\Capstone\May\incidentra-May   # atau folder clone Anda
git status
# pastikan tidak ada backend/.env atau .env.docker ter-stage
git add .
git commit -m "Deskripsi perubahan singkat"
git push origin main
```

Jika repo baru kosong (pertama kali):

```powershell
git init
git branch -M main
git remote add origin https://github.com/HardInCode/incidentra.git
git add .
git commit -m "Initial commit: Incidentra capstone"
git push -u origin main
```

---

## Cabang (opsional)

```powershell
git checkout -b feature/ip-management
# ... kerja ...
git push -u origin feature/ip-management
```

Lalu buat Pull Request di GitHub untuk review tim.

---

## Env Docker vs manual (sering membingungkan)

| Mode | File env | URL database |
|------|-----------|--------------|
| **Docker** | `backend/.env.docker` + override `docker-compose.yml` | `postgresql+psycopg://smeguard:...@postgres:5432/...` (hostname `postgres`, bukan `localhost`) |
| **Manual** | `backend/.env` | `postgresql+psycopg://...@localhost:5432/...` |

**Jangan** mengisi `DATABASE_URL=localhost` di `.env.docker` — di dalam container itu salah. DB/Redis sudah di-set di `docker-compose.yml`.

Frontend Docker: `REACT_APP_API_URL` di-bake saat **build** (`docker compose build frontend`). Ubah IP server → rebuild frontend (lihat [DEPLOY.md](DEPLOY.md)).

### AI / Groq tidak jalan di Docker

1. Isi `GROQ_API_KEY=gsk_...` di `backend/.env.docker` (bukan hanya di `.env` manual).
2. Restart backend: `docker compose up -d --build backend`
3. Atau simpan key lewat **Settings** di UI (disimpan ke tabel `app_settings`).
4. Uji: Settings → **Test Groq** atau generate explanation di detail insiden.

Backend menyalin env kosong ke DB saat startup (`seed_settings_from_env`) jika key belum ada di database.

---

*Terakhir diselaraskan: Mei 2026 — Incidentra Capstone.*
