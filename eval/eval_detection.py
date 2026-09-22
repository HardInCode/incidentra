import re
import json
from pathlib import Path

# ── Paths (portable: resolved relative to this script's location) ────────────
_SCRIPT_DIR = Path(__file__).resolve().parent

# ── Load DETECTION_PATTERNS from production source (no reimplementation) ─────
src = (_SCRIPT_DIR / "../backend/app/core/detection_engine.py").resolve().open(encoding="utf-8").read()
start = src.index("DETECTION_PATTERNS = {")
end = src.index("\n}\n", start) + 3
ns = {}
exec(src[start:end], ns)
DETECTION_PATTERNS = ns['DETECTION_PATTERNS']

# ── Load corpus (single source of truth for all samples) ─────────────────────
_corpus = json.loads((_SCRIPT_DIR / "corpus.json").read_text(encoding="utf-8"))

# benign: list of dicts with keys method / path / query / user_agent
benign_rows = _corpus["benign"]
# attacks: same as benign + "label" key
attack_rows = _corpus["attacks"]

# Validate corpus structure on load
assert len(benign_rows) == 30, f"Expected 30 benign samples, got {len(benign_rows)}"
assert len(attack_rows) == 30, f"Expected 30 attack samples, got {len(attack_rows)}"
_VALID_LABELS = {
    "SQL_INJECTION", "XSS", "PATH_TRAVERSAL", "FILE_UPLOAD",
    "COMMAND_INJECTION", "SCANNER", "LFI_RFI", "CSRF",
}
for row in attack_rows:
    assert row["label"] in _VALID_LABELS, f"Unknown label: {row['label']!r}"

# ── Compile regex patterns ────────────────────────────────────────────────────
COMPILED = {
    a: [re.compile(p) for p in v['patterns']]
    for a, v in DETECTION_PATTERNS.items() if v['patterns']
}

def classify(method, path, query, ua):
    searchable = f"{method} {path} {query} {ua}"
    for attack_type, patterns in COMPILED.items():
        for p in patterns:
            if p.search(searchable):
                return attack_type
    return None  # benign / no-match

def evaluate():
    per_cat = {a: {"tp": 0, "fn": 0} for a in DETECTION_PATTERNS if a != "BRUTE_FORCE"}
    fp = 0
    tn = 0
    fp_examples = []
    fn_examples = []

    for row in benign_rows:
        pred = classify(row["method"], row["path"], row["query"], row["user_agent"])
        if pred is None:
            tn += 1
        else:
            fp += 1
            fp_examples.append((row["method"], row["path"], row["query"], pred))

    for row in attack_rows:
        label = row["label"]
        pred = classify(row["method"], row["path"], row["query"], row["user_agent"])
        if pred == label:
            per_cat[label]["tp"] += 1
        else:
            per_cat[label]["fn"] += 1
            fn_examples.append((row["method"], row["path"], row["query"], label, pred))

    total_tp = sum(v["tp"] for v in per_cat.values())
    total_fn = sum(v["fn"] for v in per_cat.values())
    total_fp = fp
    total_tn = tn

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0
    recall    = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    fpr       = total_fp / (total_fp + total_tn) if (total_fp + total_tn) else 0

    print(f"corpus.json  ->  benign={len(benign_rows)}  attacks={len(attack_rows)}")
    print(f"TP={total_tp} FN={total_fn} FP={total_fp} TN={total_tn}")
    print(f"Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}  FPR={fpr:.3f}")
    print()
    print("Per-category (attack samples only):")
    for cat, v in per_cat.items():
        total = v["tp"] + v["fn"]
        rec = v["tp"] / total if total else float('nan')
        if total:
            print(f"  {cat:18s} n={total:2d}  TP={v['tp']:2d}  FN={v['fn']:2d}  recall={rec:.2f}")
        else:
            print(f"  {cat:18s} n=0 (not tested)")
    print()
    print("False positives (benign misclassified):")
    for m, p, q, pred in fp_examples:
        print(f"  {m} {p}?{q}  -> flagged as {pred}")
    print()
    print("False negatives (attacks missed):")
    for m, p, q, label, pred in fn_examples:
        print(f"  [{label}] {m} {p}?{q}  -> predicted {pred}")

    return {
        "tp": total_tp, "fn": total_fn, "fp": total_fp, "tn": total_tn,
        "precision": precision, "recall": recall, "f1": f1, "fpr": fpr,
        "per_cat": per_cat, "fp_examples": fp_examples, "fn_examples": fn_examples,
    }

if __name__ == "__main__":
    evaluate()
