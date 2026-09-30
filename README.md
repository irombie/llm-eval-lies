# Your LLM Evaluation Is Lying to You

Companion code for my talk at AI Connect Istanbul. Small, readable scripts that show how LLM evals mislead, and how to catch it.

## What's here

| File | What it shows |
| --- | --- |
| `eval.py` + `dataset.jsonl` | A complete eval for one capability (support ticket routing): deterministic scorer, CI gate, and a `--runs` flag that shows the noise floor |
| `judge_flip.py` | Position bias in an LLM judge: same two answers, swap the order, count the verdicts |
| `jev_examples.py` | Example Jev questions (Noul, Score, Choice) as DeepEval JevEval metrics |

## Quick start (no API key needed)

```bash
python eval.py --mock              # one run, scored and gated
python eval.py --mock --runs 5     # five runs: watch the score move with nothing changed
python judge_flip.py --mock        # a judge with built-in position bias
```

`--mock` swaps in a simulated model so you can see each effect in seconds. The mock numbers illustrate the effect; they are not results.

## With a real model

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python eval.py --runs 5
python judge_flip.py --n 20 --model <judge-model>
```

Each script has one function to swap for your own provider: `call_model` in `eval.py`, `call_judge` in `judge_flip.py`.

## Make it yours

The code is generic. The value is in `dataset.jsonl`. Replace the rows with 20 or so examples from your real traffic, labeled by hand, and your eval starts telling you the truth about your task.

## References

See the last slides of the talk, or:

- Zheng et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. arXiv:2306.05685
- Thakur et al. (2025). Judging the Judges. arXiv:2406.12624
- When AI Benchmarks Plateau (2026). arXiv:2602.16763
- Li et al. (2026). JEV-as-a-Judge. arXiv:2609.26550
- Ahuja et al. (2024). MEGAVERSE. arXiv:2311.07463
