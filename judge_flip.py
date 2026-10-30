"""
Position-bias demo for an LLM judge.

Same question, same two answers, same judge. The only thing that changes
is which answer is shown first. If the judge were unbiased, the winner
would not depend on the order.

Run:
    python judge_flip.py --mock --seed 2     # no API key: fake judge with a built-in position bias
    python judge_flip.py                     # real judge, 10 trials per order
    python judge_flip.py --n 20 --model <judge-model>
    python judge_flip.py --temperature 0     # near-deterministic: one clean flip or none

Note: newer models (Claude 4.7 and later) reject a non-default temperature, so
--temperature is only sent when you pass it. Leave it out for those models.
"""

import argparse
import os
import random
import re

# Override with --model or the JUDGE_MODEL environment variable.
DEFAULT_JUDGE = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-6")

JUDGE_PROMPT = """You are an impartial judge. Below is a user question and two responses.
Decide which response is better overall, considering accuracy,
helpfulness and clarity. Reply with only the letter A or B.

[Question]
{question}

[Response A]
{response_a}

[Response B]
{response_b}"""

QUESTION = "Explain what a database index is to a junior developer."

ANSWER_1 = (
    "Think of a book's index. Instead of reading every page to find "
    '"recursion," you check the index and jump straight to page 212. A '
    "database index works the same way: it keeps a sorted lookup of a "
    "column's values so the database can find matching rows without "
    "scanning the whole table. The trade-off is that every insert or "
    "update also has to update the index."
)

ANSWER_2 = (
    "An index is a separate data structure, usually a B-tree, that stores "
    "a column's values in sorted order along with pointers to the rows. "
    "When you filter on that column, the database searches the tree "
    "instead of scanning every row, which turns a full scan into a fast "
    "lookup. The cost is extra storage and slower writes, since the index "
    "must stay in sync."
)


# --- the ONE function you swap for your provider ---------------------------
def call_judge(prompt, model, temperature, mock=False):
    if mock:
        return _mock_judge(prompt)
    # pip install anthropic ; export ANTHROPIC_API_KEY=...
    import anthropic
    client = anthropic.Anthropic()
    kwargs = {"temperature": temperature} if temperature is not None else {}
    resp = client.messages.create(
        model=model,
        max_tokens=5,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return resp.content[0].text
# ---------------------------------------------------------------------------


def parse_verdict(raw):
    """Return 'A', 'B', or None. Takes the first standalone A or B."""
    match = re.search(r"\b([AB])\b", raw.strip().upper())
    return match.group(1) if match else None


def run_order(first, second, n, model, temperature, mock):
    """Run n trials with `first` in slot A. Returns (slot_a_wins, slot_b_wins, invalid)."""
    prompt = JUDGE_PROMPT.format(question=QUESTION, response_a=first, response_b=second)
    a = b = bad = 0
    for _ in range(n):
        v = parse_verdict(call_judge(prompt, model, temperature, mock))
        if v == "A":
            a += 1
        elif v == "B":
            b += 1
        else:
            bad += 1
    return a, b, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="Swap the answer order, count the judge's verdicts.")
    ap.add_argument("--n", type=int, default=10, help="trials per order")
    ap.add_argument("--model", default=DEFAULT_JUDGE, help="judge model id")
    ap.add_argument("--temperature", type=float, default=None,
                    help="sampling temperature (omitted from the request unless set)")
    ap.add_argument("--mock", action="store_true", help="simulated biased judge, no API key needed")
    ap.add_argument("--seed", type=int, default=None, help="seed the mock judge for repeatable output")
    args = ap.parse_args(argv)

    if args.seed is not None:
        random.seed(args.seed)

    run = dict(n=args.n, model=args.model, temperature=args.temperature, mock=args.mock)

    # Order 1: Answer 1 shown first (slot A)
    a1, b1, bad1 = run_order(ANSWER_1, ANSWER_2, **run)
    # Order 2: Answer 2 shown first (slot A)
    a2, b2, bad2 = run_order(ANSWER_2, ANSWER_1, **run)

    ans1_when_first, ans1_when_second = a1, b2
    ans2_when_first, ans2_when_second = a2, b1
    valid = (a1 + b1) + (a2 + b2)
    first_slot_rate = (a1 + a2) / valid if valid else 0.0

    temp = "model default" if args.temperature is None else args.temperature
    judge = "mock judge" if args.mock else f"{args.model}, temperature {temp}"
    print(f"Judge: {judge}   Trials per order: {args.n}\n")
    print("                  shown FIRST    shown SECOND")
    print(f"Answer 1 wins     {ans1_when_first:>3}/{a1 + b1:<3}        {ans1_when_second:>3}/{a2 + b2:<3}")
    print(f"Answer 2 wins     {ans2_when_first:>3}/{a2 + b2:<3}        {ans2_when_second:>3}/{a1 + b1:<3}")
    if bad1 or bad2:
        print(f"\nunparseable verdicts: {bad1 + bad2} (excluded)")

    print(f"\nFirst slot wins {first_slot_rate:.0%} of all verdicts. An order-blind judge sits near 50%.")
    swing = ans1_when_first / max(a1 + b1, 1) - ans1_when_second / max(a2 + b2, 1)
    print(f"Answer 1's win rate moves {swing:+.0%} just from its position.")
    if abs(swing) < 0.2:
        print("Small swing: this judge may not show strong position bias on this item.")
        print("Try a different judge model, or make the two answers even closer in quality.")


# A stand-in judge with a built-in position bias, so the demo runs with no API key.
# It has a slight real preference for Answer 1 and a stronger preference for slot A.
def _mock_judge(prompt):
    a_block = prompt.split("[Response A]")[1].split("[Response B]")[0]
    slot_a_is_answer_1 = "book's index" in a_block
    p_pick_a = 0.70 + (0.05 if slot_a_is_answer_1 else -0.05)
    if random.random() < 0.03:
        return "Both are good, but I lean toward the first."  # unparseable, like real judges sometimes
    return "A" if random.random() < p_pick_a else "B"


if __name__ == "__main__":
    main()
