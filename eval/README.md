# Incidentra Detection-Accuracy Evaluation (Reproducibility Artifact)

Produced for the ICIC2026 camera-ready to address reviewer requests for
precision/recall/F1 metrics on benign + attack traffic and a reproducible
evaluation dataset.

## Contents
- `corpus.json` — 30 labeled benign requests + 30 labeled attack-payload
  variants across 8 regex-based categories (brute force excluded; it is
  threshold-based, already validated functionally in Table III of the paper).
- `eval_detection.py` — loads `DETECTION_PATTERNS` directly from
  `../backend/app/core/detection_engine.py` (relative to this script's
  location; path is resolved via `pathlib` so the script is portable).
  Classifies every corpus sample and reports precision, recall, F1, and
  false-positive rate. Also includes a 50,000-line synthetic-traffic throughput
  benchmark (component-level regex-matching speed, not a full concurrent-load
  system stress test).

## How to run
```bash
# Run from the incidentra repo root (eval/ must be a direct subfolder)
python eval/eval_detection.py
```

## Results (as reported in the paper)
| Metric | Value |
|---|---|
| Precision | 1.00 |
| Recall | 0.87 |
| F1-score | 0.93 |
| False-positive rate | 0.00 |
| Regex-matching throughput | ~12,800 lines/s (single core) |

## Known limitations
- Synthetic corpus (60 samples), not captured production traffic.
- Two SQL-injection variants (type-cast / blind) were missed; one
  command-injection sample was mis-tagged as path traversal due to
  first-match category resolution in the engine.
- Throughput figure is component-level (regex matching only), not a
  full end-to-end concurrent-load stress test (Docker + Redis + Postgres
  under load). Full-system stress testing is noted as future work.
