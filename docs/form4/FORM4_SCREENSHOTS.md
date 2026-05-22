# Form 4 — Screenshot checklist (May 2026)

Run `docker compose up -d` before capture. Check `[x]` when done.

**Part B in Word:** you already have full screenshots — use this list to verify nothing is missing.

---

## Required (defense minimum)

| # | File (suggested) | Action | [ ] |
|---|------------------|--------|-----|
| 1 | `fig01-login.png` | SOC login | |
| 2 | `fig02-dashboard.png` | Dashboard KPI + charts | |
| 3 | `fig03-incidents-ongoing.png` | **Ongoing** `/incidents` | |
| 3b | `fig03b-incidents-all.png` | **All** `/incidents/all` with resolved row | |
| 4 | `fig04-incident-detail.png` | Detail + raw payload | |
| 5 | `fig05-ai-explanation.png` | After Generate AI | |
| 6 | `fig06-ip-mgmt-blocked.png` | IP Management → Blocked | |
| 7 | `fig07-ip-mgmt-rate.png` | IP Management → Rate Limited | |
| 8 | `fig08-rules.png` | Detection Rules + lab ⓘ | |
| 9 | `fig10-live-traffic.png` | Attack **200** then Blocked **403** | |
| 10 | `fig13-vuln-403.png` | vuln-web 403 | |
| 11 | `fig14-vuln-429.png` | vuln-web 429 | |

---

## Strongly recommended (v2 features)

| # | File | Action | [ ] |
|---|------|--------|-----|
| 12 | `fig15-ip-history.png` | IP History drawer open | |
| 13 | `fig16-whitelist.png` | Whitelist success / enforcement label | |
| 14 | `fig17-export-ongoing.png` | Export dialog on ongoing page | |
| 15 | `fig18-export-all.png` | Export on all page + filename hint | |
| 16 | `fig19-bulk-resolve.png` | Multi-select → resolved toast | |
| 17 | `fig20-chatbot.png` | Chatbot FAB + reply | |
| 18 | `fig21-notification.png` | Bell badge / toast | |
| 19 | `fig22-session-timeout.png` | Idle warning dialog | |
| 20 | `fig23-lab-mode.png` | Settings lab mode ON + rules warning | |
| 21 | `fig24-phase3-banner.png` | vuln-web red Phase 3 banner | |
| 22 | `fig25-settings-groq.png` | Settings test connection success | |
| 23 | `fig26-error-login.png` | Wrong password / 401 | |

---

## Demo order (one session)

1. Reset ([FORM4_IMPLEMENTATION_v2.md](FORM4_IMPLEMENTATION_v2.md) § E.1)
2. Dashboard clean
3. SQLi login → ongoing → 403
4. Resolve → show in **All Incidents**
5. Export ongoing CSV vs all CSV (different files)
6. Unblock → XSS → Live Traffic two-phase
7. IP History → whitelist → verify no 403
8. Optional: lab mode demo ([../AUDIT.md](../AUDIT.md) § I)

Store under `docs/form4/screenshots/` if archiving for team.

---

*Checklist aligned with FORM4_IMPLEMENTATION_v2.md and AUDIT.md.*
