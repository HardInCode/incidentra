# Scripts

Jalankan dari **root proyek** (venv backend aktif). Detail: [../docs/GUIDE.md](../docs/GUIDE.md) (bagian skrip utilitas)

| File | Fungsi |
|------|--------|
| `init_postgres.sql` | User & database PostgreSQL |
| `reset_incidentra.py` | Kosongkan insiden, blokir, rate limit JSON, Redis, audit |
| `seed_chart_demo.py` | Seed insiden 7 hari untuk grafik Dashboard |

**Setelah reset:** restart backend (dan vuln-web jika perlu).
