# Scripts

Run from the **project root** (backend venv active). Details: [../docs/GUIDE.md](../docs/GUIDE.md) (utility scripts section)

| File | Purpose |
|------|---------|
| `init_postgres.sql` | Create PostgreSQL user & database |
| `reset_incidentra.py` | Clear incidents, blocks, rate limit JSON, Redis, audit |
| `reset_incidentra_docker.ps1` | Docker wrapper for reset script |
| `seed_chart_demo.py` | Seed incidents over 7 days for Dashboard charts |
| `seed_chart_docker.ps1` | Docker wrapper for chart seed script |

**After reset:** restart backend (and vuln-web if needed).
