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
- **PATH_TRAVERSAL** — high → escalating block (not permanent)
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

## June 2026 — Escalating block policy (Form 5 alignment)

- **Auto-response revised:** high/critical → `escalating_block` (no automatic permanent block)
- **Repeat Offender:** `BlockedIP.is_repeat_offender`, configurable threshold (default 3)
- **Settings:** `REPEAT_OFFENDER_THRESHOLD`, `ESCALATING_HIGH_DURATIONS`, `ESCALATING_CRITICAL_DURATIONS`
- **Redis persistence:** `escalation_count:{ip}`, `escalation_severity:{ip}` survive admin unblock (30-day TTL)
- **Legacy actions:** `temporary_block` / `permanent_block` retained for manual API calls only
- **Docs synced:** Form 5, `DETECTION.md`, `ARCHITECTURE.md`, `AUDIT.md`, `GUIDE.md`, Form 4 v5
- **Seed count corrected:** 18 detection rules (11 core + 7 `EXTRA_RULES`), not 11

---

## June 2026 — Form 5 cross-check (v5 doc touch-up)

- **Part D testing:** PATH_TRAVERSAL, FILE_UPLOAD, BRUTE_FORCE expected outcomes aligned to escalating block (high → Offense #1 ~1h, HTTP 403), not legacy 24h temp block or rate-limit 429
- **Part B Settings:** removed stale "temporary block duration" UI reference; documents Escalating Block Policy section
- **Part B/C IP Management:** Repeat Offender badge and filter documented
- **Section 1.3 / 5:** client-feedback context (Form 5) and Redis escalation persistence on unblock

---

## June 2026 — Word export sync (FORM4_IMPLEMENTATION_v5.md full doc)

- **Figure 4 / Figure 7:** RESPONSE_ACTIONS and respond() snippets aligned to `escalating_block` (removed stale permanent/temporary auto-block flow)
- **Part D:** D.2–D.6 expected outputs; new **D.20** Escalating Block / Repeat Offender
- **§2 / §3 / E.1:** 18 seeded rules, analyst user, 3 IP Management tabs, `is_repeat_offender`, 15s dashboard refresh
- **Part B:** Incident Detail automated action wording; date June 2026

---

## June 2026 — Form 1 & Form 2 alignment

- **Naming:** SME-Guard → Incidentra (consistent with Forms 3–5)
- **Form 1 §4.1.2:** escalating block policy (no auto permanent block); demo env vuln-web + Docker Compose
- **Form 2:** proposed process, use cases, operational env, automated response (P2), data dictionary updated

---

## June 2026 — Team roster (Nasywa removed)

- **Forms 1–5:** group member, Statement of Originality, Signer 1–2
- **Form 1:** manpower (2 rows), dev hardware 2x laptops
- **Form 2:** product dev env 2 laptops
- **Form 4 v5 Table 6:** Developer laptop 3 → **2**; total **~Rp 25.650.000**
- **Also updated:** `FORM4_COVER.md`, `FORM4_IMPLEMENTATION.md` footer, `GEMINI_SLIDES_PROMPT.md`, `docs/ARCHITECTURE.md` Tim table

---

*Copy sections A, C, D, E from v2 into Word; keep Part B from your Word screenshots.*
