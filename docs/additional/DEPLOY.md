# Docker, port, dan deploy (capstone)

Dokumen ini untuk **deploy nilai tambah**: sistem jalan di **server asli** (VPS/VM), diakses lewat IP/domain — bukan production penuh (HTTPS/WAF opsional).

**Repo:** [github.com/HardInCode/sme-guard](https://github.com/HardInCode/sme-guard)  
Lihat juga: [../GUIDE.md](../GUIDE.md), [../ARCHITECTURE.md](../ARCHITECTURE.md), [GITHUB.md](GITHUB.md).

---

## Yang dimaksud dosen “deploy di server asli”

| Yang dicari (capstone) | Bukan wajib (production sungguhan) |
|------------------------|-------------------------------------|
| Aplikasi jalan di VPS/VM (DigitalOcean, AWS EC2, dll.) | Hardening keamanan penuh |
| Dosen/tim akses lewat `http://IP_SERVER:3000` | HTTPS + sertifikat wajib |
| Tiap komponen **bisa** ditunjukkan hidup di server | Pisah ke banyak region / auto-scale |
| Demo serangan + SOC tetap jalan (termasuk vuln-web lab) | Ganti vuln-web dengan website klien nyata |
| Docker Compose **atau** manual di Linux | Audit SOC2, backup terjadwal, dll. |

**Intinya:** bukti sistem tidak cuma di laptop — stack SME-Guard (dashboard, API, DB, target lab) hidup di satu (atau beberapa) mesin yang bisa dibuka dari jaringan.

---

## Port resmi (sama di laptop & server)

| Layanan | Port | Peran |
|---------|------|--------|
| Frontend (UI) | **3000** | Dashboard SOC |
| Backend API | **5000** | REST API |
| Vuln-web (lab) | **5050** | Target demo serangan |
| PostgreSQL | 5432 | Database (internal) |
| Redis | 6379 | Cache / Celery |

Manual vs Docker: **port sama**; bedanya path file & hostname DB (`localhost` vs `postgres` di Docker). Tabel env: lihat bagian bawah dokumen ini.

---

## Deploy capstone — rekomendasi termudah (1 VPS + Docker)

Cocok untuk nilai tambah tanpa ribet banyak server.

### 1. Siapkan VPS Linux

- Ubuntu 22.04, RAM minimal 2 GB
- Buka firewall / security group: port **3000**, **5000**, **5050** (dan 22 untuk SSH)

### 2. Install Docker di VPS

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
# logout/login sekali
```

### 3. Clone & sesuaikan URL API (penting)

```bash
git clone https://github.com/HardInCode/sme-guard.git
cd sme-guard
cp backend/.env.docker.example backend/.env.docker
# edit backend/.env.docker jika perlu (GROQ_API_KEY)
```

Ganti `IP_SERVER` dengan IP publik VPS (mis. `203.0.113.10`).

Edit `docker-compose.yml` bagian frontend:

```yaml
frontend:
  build:
    args:
      REACT_APP_API_URL: http://IP_SERVER:5000/api
```

Tanpa ini, UI di browser akan tetap memanggil `localhost:5000` dan gagal saat dibuka dari laptop dosen.

Opsional di `backend/.env.docker`:

```env
CORS_ORIGINS=http://IP_SERVER:3000
```

### 4. Jalankan

```bash
docker compose up --build -d
docker compose ps
docker compose logs backend --tail 20
```

### 5. Yang ditunjukkan ke dosen

| URL | Isi |
|-----|-----|
| `http://IP_SERVER:3000` | Login SOC (`admin` / `Admin@Incidentra2026!`) |
| `http://IP_SERVER:5050` | Vuln-web (target serangan) |
| `http://IP_SERVER:5000/api/dashboard/stats` | Bukti API hidup (butuh token jika protected) |

Lakukan 1 serangan SQLi di :5050 → insiden muncul di dashboard :3000 → IP terblokir. Itu sudah membuktikan **pipeline di server asli**.

---

## Deploy capstone — nilai tambah lebih (beberapa server)

Kalau dosen ingin “tiap server pakai server asli” secara terpisah:

```
[ VPS A ]  Frontend :3000
[ VPS B ]  Backend  :5000  + PostgreSQL + Redis
[ VPS C ]  Vuln-web  :5050
```

Yang perlu diubah:

| Komponen | Setting |
|----------|---------|
| Frontend build | `REACT_APP_API_URL=http://IP_VPS_B:5000/api` |
| Backend `.env` | `DATABASE_URL` ke Postgres di VPS B; `WEB_SERVER_LOG_PATH` — **sulit** jika log di VPS C (perlu NFS/shared folder atau satu mesin untuk log+backend) |
| CORS backend | `CORS_ORIGINS=http://IP_VPS_A:3000` |

**Catatan praktis:** log monitor butuh backend bisa **baca file log** vuln-web. Untuk capstone, **satu VPS + Docker Compose** (volume log bersama) jauh lebih mudah daripada 3 VM tanpa shared storage. Jika tetap multi-VM, jelaskan di laporan: “arsitektur terdistribusi; log dikirim lewat …” atau satukan backend+vuln-web di VPS yang sama.

---

## Manual di server (tanpa Docker)

Tetap valid untuk nilai tambah:

1. Install PostgreSQL, Redis, Python 3.11, Node 18 di VPS  
2. Ikuti [../GUIDE.md](../GUIDE.md) Opsi B, dengan `.env` backend:

```env
DATABASE_URL=postgresql://smeguard:smeguard123@localhost:5432/smeguard_db
WEB_SERVER_LOG_PATH=../vuln-web/logs/access.log
# ...
```

3. Frontend production build:

```bash
cd frontend
REACT_APP_API_URL=http://IP_SERVER:5000/api npm run build
# sajikan folder build/ dengan nginx di port 3000 atau 80
```

4. Backend: `gunicorn -b 0.0.0.0:5000 run:app` + pastikan log monitor jalan (lihat `docker_log_monitor.py` / `run.py`)

5. Vuln-web: `python app.py` di port 5050, bind `0.0.0.0`

Jalankan dengan `screen`/`tmux` atau systemd — untuk capstone, `tmux` 3 pane sudah cukup dibuktikan di screenshot.

---

## File Docker — ringkas

| File | Fungsi |
|------|--------|
| `docker-compose.yml` | Satu perintah jalankan postgres, redis, vuln-web, backend, celery, frontend |
| `backend/Dockerfile` + `docker_entrypoint.sh` | Image API + init DB + log monitor + gunicorn |
| `backend/docker_log_monitor.py` | Tail log (setara bagian `run.py` saat manual) |
| `backend/.env.docker.example` | Template (di repo) |
| `backend/.env.docker` | Env lokal (buat dari example, tidak di-commit) |
| `backend/docker_entrypoint.sh` | Init DB (`postgresql+psycopg`), gunicorn, log monitor |
| `frontend/Dockerfile` | Build React → nginx |
| Volume `vuln_logs` | `access.log` + JSON blokir dibagi backend ↔ vuln-web |

**Di laptop Windows:** sama, pakai Docker Desktop — lihat [../GUIDE.md](../GUIDE.md) Opsi A.

---

## Env manual vs Docker

| Folder | Manual (laptop/server) | Docker |
|--------|------------------------|--------|
| `backend/` | `.env` dari `.env.example` | `.env.docker` (dari example) + **compose override** untuk `DATABASE_URL` / `REDIS_URL` |
| `frontend/` | `.env` atau proxy `package.json` | build arg `REACT_APP_API_URL` |
| `vuln-web/` | `.env` (`VULN_PORT=5050`) | env service `vuln_web` di compose |

**Penting:** Jangan set `DATABASE_URL=...@localhost` di `.env.docker` di dalam container — hostname DB adalah `postgres`.

---

## Troubleshooting Docker (laptop atau VPS)

| Masalah | Solusi |
|---------|--------|
| Port sudah dipakai | Matikan proses manual di 3000/5000/5050 |
| UI tidak load data | `REACT_APP_API_URL` harus IP/domain yang dibuka browser, bukan `localhost` di mesin dosen |
| Backend restart | `docker compose logs backend` — pastikan `postgresql+psycopg://` di compose |
| Build frontend ajv | `docker compose build --no-cache frontend` |
| Docker Desktop mati | Jalankan Docker Desktop dulu (Windows) |
| Firewall | Buka port di panel cloud + `ufw` jika aktif |

---

## Production sungguhan (di luar scope capstone)

Hanya jika nanti dipakai di industri: HTTPS, secret kuat, Postgres tidak publik, log dari website klien (bukan vuln-web), backup DB. **Tidak perlu untuk nilai deploy capstone** kecuali dosen meminta eksplisit.

---

## Ringkasan

| Pertanyaan | Jawaban |
|------------|---------|
| Deploy untuk capstone? | **VPS + `docker compose`**, akses `http://IP:3000` — ubah `REACT_APP_API_URL` ke IP server |
| Harus production? | **Tidak** — server asli + demo end-to-end sudah nilai tambah |
| Vuln-web ikut? | **Ya** untuk lab capstone |
| Struktur repo clean? | **Ya** — `backend`, `frontend`, `vuln-web`, `scripts`, `docs`, `docker-compose.yml` |
