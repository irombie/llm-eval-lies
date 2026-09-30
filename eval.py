"""
A tiny, honest eval for ONE capability: structured intent extraction.

The model reads a support message and must return:
    {"category": one of ["billing","technical","account","other"],
     "priority": one of ["low","high"]}

Why this shape for a talk:
  - Closed answer space -> the scorer is deterministic. No LLM judge, so the
    eval itself is not lying to you. (Use a judge only for open-ended fields.)
  - The examples ARE the eval. Pull them from real traffic, label by hand,
    version them in dataset.jsonl. Everything below is just plumbing.

Run:
    python eval.py --mock            # no API key: exercises the harness itself
    python eval.py                   # real model, single pass, CI gate
    python eval.py --runs 5          # 5 passes: is your "win" bigger than the noise?
"""

import argparse
import json
import random
import re
import statistics
from pathlib import Path

CATEGORIES = {"billing", "technical", "account", "other"}
PRIORITIES = {"low", "high"}

PROMPT = """You are a support ticket router. Reply with ONLY a JSON object:
{{"category": one of ["billing","technical","account","other"], "priority": one of ["low","high"]}}
No prose, no code fences.

Message: {message}"""


def load_dataset(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


# --- the ONE function you swap for your provider ---------------------------
def call_model(message, mock=False):
    if mock:
        return _mock_model(message)
    # pip install anthropic ; export ANTHROPIC_API_KEY=...
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=100,
        messages=[{"role": "user", "content": PROMPT.format(message=message)}],
    )
    return resp.content[0].text
# ---------------------------------------------------------------------------


def parse(raw):
    """Tolerant JSON extraction. If we cannot find a JSON object, the model failed."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)  # survives ```json fences and stray prose
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def score_one(pred, gold):
    """Deterministic. Returns (0/1, reason). Order of checks tells you WHY it failed."""
    if pred is None:
        return 0, "invalid_json"
    if pred.get("category") not in CATEGORIES or pred.get("priority") not in PRIORITIES:
        return 0, "off_schema"
    ok = pred["category"] == gold["category"] and pred["priority"] == gold["priority"]
    return (1, "correct") if ok else (0, "wrong")


def run_once(data, mock=False):
    correct, failures = 0, []
    for row in data:
        pred = parse(call_model(row["message"], mock=mock))
        s, why = score_one(pred, row["label"])
        correct += s
        if s == 0:
            failures.append((why, row["message"][:48]))
    return correct / len(data), failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="dataset.jsonl")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--threshold", type=float, default=0.80)  # your CI gate
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    data = load_dataset(args.data)

    # Multi-run: the honest way to report a score. One number is not a result.
    if args.runs > 1:
        scores = []
        for i in range(args.runs):
            acc, _ = run_once(data, mock=args.mock)
            scores.append(acc)
            print(f"  run {i + 1}: {acc:.1%}")
        lo, hi = min(scores), max(scores)
        spread = hi - lo
        print(f"\nmean {statistics.mean(scores):.1%}  "
              f"stdev {statistics.pstdev(scores):.1%}  range [{lo:.1%}, {hi:.1%}]")
        print(f"noise floor this run: {spread:.1%}. "
              f"A change smaller than that is not a result, it is variance.")
        return

    # Single run: score, show what broke, then gate.
    acc, failures = run_once(data, mock=args.mock)
    print(f"accuracy: {acc:.1%} on {len(data)} examples\n")
    if failures:
        print("failures (fix these before you trust the number):")
        for why, msg in failures:
            print(f"  [{why:12}] {msg}")
    passed = acc >= args.threshold
    print(f"\ngate: {'PASS' if passed else 'FAIL'} (threshold {args.threshold:.0%})")
    raise SystemExit(0 if passed else 1)  # non-zero exit fails CI


# A deliberately imperfect stand-in so the harness runs with no API key,
# and so --runs shows real run-to-run spread (it injects a little noise).
def _mock_model(message):
    m = message.lower()
    if "charge" in m or "refund" in m or "invoice" in m or "plan" in m or "discount" in m:
        cat = "billing"
    elif "password" in m or "account" in m or "email" in m or "teammate" in m or "authentication" in m:
        cat = "account"
    elif "crash" in m or "down" in m or "error" in m or "export" in m or "dashboard" in m:
        cat = "technical"
    else:
        cat = "other"
    urgent = any(w in m for w in ["twice", "crash", "down", "blocked", "not work",
                                  "wrong", "500", "locking", "unauthorize", "did not"])
    pri = "high" if urgent else "low"
    if random.random() < 0.12:            # ~12% of the time the model slips
        pri = "low" if pri == "high" else "high"
    if random.random() < 0.05:            # ~5% of the time it returns junk JSON
        return "Sure! Here is the category: " + cat
    return json.dumps({"category": cat, "priority": pri})


if __name__ == "__main__":
    main()
