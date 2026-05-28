# Form 4 Implementation — Revision log (v1 → v2)

**Date:** May 2026  
**Keep:** `FORM4_IMPLEMENTATION.md` (archive for compare)  
**New:** `FORM4_IMPLEMENTATION_v2.md`

---

## Added in v2

- **Code snippets** for every Form 3 subsystem (log_parser, log_monitor, detection_engine, response_manager, key API blueprints, React pages) — template requirement A.1
- **Ongoing Incidents** `/incidents` vs **All Incidents** `/incidents/all` — routes, filters, sidebar (`Layout.js`)
- **Export CSV** scoped: `list_scope=ongoing|all`, filenames `incidents-ongoing.csv` / `incidents-all.csv`
- **IP History drawer** — `IPHistoryDrawer.js`, `GET /api/ip/<ip>/history`
- **Whitelist IP** — `is_whitelist`, upsert on existing row, skip detection, excluded from `blocked_ips.json`
- **Bulk resolve** (admin) — selection mode in `Incidents.js`, `PATCH /api/incidents/bulk-status`
- **Chatbot widget** — `ChatbotWidget.js`, `/api/chatbot`, draggable FAB (May 2026 UX)
- **Notification bell** — `NotificationBell.js`, toast + badge; email/Telegram via Settings
- **Session timeout warning** — `SessionTimeoutWarning.js`
- **Lab mode** — `settings_reader.is_lab_mode_ui_only()`, UI rules only when ON
- **Phase 3** — `VULN_UNSAFE_CMD`, `VULN_UNSAFE_UPLOAD` in `docker-compose.yml`
- **Live Traffic** — explicit separation from detection (`traffic.py` header comment)
- **PATH_TRAVERSAL** — high → temporary block (not permanent)
- **May 2026 block fix** — `_block_ip` returns `bool`; auto-block sets `is_whitelist=False`
- **Part D** — separate tables: Export CSV, All Incidents nav, IP History + Whitelist, Lab mode, Notifications, Bulk resolve
- **Part B** — figure index only (screenshots in user Word doc); no 50+ `[SCREENSHOT:]` placeholders
- **Cross-links** — `../AUDIT.md`, `../DETECTION.md`, `../GUIDE.md`

---

## Corrected vs v1

- Export filename was always `incidents.csv` in older text — now documents distinct names
- Whitelist 409 on existing IP — documents upsert path in `blocked_ips.py`
- Detection skip for whitelisted IPs — `detection_engine.py` early return
- Audit reference path → `AUDIT.md` (merged docs)

---

## Unchanged (by design)

- `FORM4_IMPLEMENTATION.md` not overwritten
- Part B primary source: user Word document with full screenshots
- Cost analysis structure (Section C)
- English formal tone for Form 4 body

---

## Docs repo merge (same revision pass)

| Old | New |
|-----|-----|
| `TUTORIAL.md` | `GUIDE.md` |
| `APPLICATION.md` | `ARCHITECTURE.md` |
| `DETECTION-GUIDE.md` + `SECURITY-LAB.md` | `DETECTION.md` |
| `AUDIT_FULL_MEI_2026.md` | `AUDIT.md` |
| `FIX-HANDOFF-PROMPT.md` | `archive/FIX-HANDOFF-PROMPT.md` |
| `Untitled` | deleted |

---

*Copy sections A, C, D, E from v2 into Word; keep Part B from your Word screenshots.*
