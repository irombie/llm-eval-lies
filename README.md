# Your LLM Evaluation Is Lying to You

[![eval](https://github.com/irombie/llm-eval-lies/actions/workflows/eval.yml/badge.svg)](https://github.com/irombie/llm-eval-lies/actions/workflows/eval.yml)

Companion code for my talk at **AI Connect Istanbul** (September 30, 2026). Small, readable scripts that show how LLM evals mislead you, and the cheap habits that catch it.

**Slides:** [Your LLM Evaluation Is Lying to You](https://claude.ai/artifact/1p37yFYAYwChzxxPs4bNk8)

Every script runs in seconds with `--mock`, no API key needed.

## The talk in one table

| The lie | Why it's false | The fix | In this repo |
| --- | --- | --- | --- |
| "It beats the big model on the benchmark." | Saturation and contamination | Ask what survives decontamination; build 20 examples from your own failures | `dataset.jsonl` |
| "The LLM judge said it improved." | Judges have position, verbosity and self-preference bias | Calibrate against human labels, randomize answer order | `judge_flip.py` |
| "My agent works. It called all the tools." | Right calls can still fail the task | Score the whole trajectory | `jev_examples.py` (tool error handling) |
| "It works." | Tiny n, one run, English only | Held-out set, several runs, test the languages you serve | `eval.py --runs 5` |

## What's here

| File | What it shows |
| --- | --- |
| `eval.py` + `dataset.jsonl` | A complete eval for one capability (support ticket routing): deterministic scorer, failure reasons, CI gate, and a `--runs` flag that shows the noise floor |
| `judge_flip.py` | Position bias in an LLM judge: same two answers, swap the order, count the verdicts |
| `jev_examples.py` | Jev questions (Noul, Score, Choice) as DeepEval `JevEval` metrics, including a Turkish RAG check |
| `tests/` | Tests for the harness itself: parser, scorer, schema checks, gate exit codes |
| `.github/workflows/eval.yml` | Runs the tests and the eval gate on every push |

## Quick start (no API key)

Python 3.10 or newer. The mock commands use only the standard library.

```bash
git clone https://github.com/irombie/llm-eval-lies.git
cd llm-eval-lies

python eval.py --mock --seed 0                 # one run, scored and gated
python eval.py --mock --runs 5 --seed 1772     # the exact numbers on the noise slide
python judge_flip.py --mock --seed 2           # a judge with built-in position bias
```

`--mock` swaps in a simulated model so you can see each effect immediately. The mock numbers illustrate the effect; they are not results about any real model. `--seed` makes the mock repeatable.

### What you should see

A single run tells you the score **and why each example failed**:

```text
accuracy: 93.3% on 15 examples

failures (fix these before you trust the number):
  [wrong       ] Where can I download last year's invoices?

gate: PASS (threshold 80%)
```

Five runs of the same model on the same data:

```text
  run 1: 86.7%
  run 2: 73.3%
  run 3: 73.3%
  run 4: 93.3%
  run 5: 80.0%

mean 81.3%  stdev 7.8%  range [73.3%, 93.3%]
noise floor this run: 20.0%. A change smaller than that is not a result, it is variance.
```

The judge, with only the answer order changed:

```text
                  shown FIRST    shown SECOND
Answer 1 wins       8/10           4/10
Answer 2 wins       6/10           2/10

First slot wins 70% of all verdicts. An order-blind judge sits near 50%.
Answer 1's win rate moves +40% just from its position.
```

Try `python judge_flip.py --mock --seed 0`: with only 10 trials per order, the same biased judge can look unbiased. That is the noise lesson again. Use `--n 50` or more before you conclude anything about your judge.

## With a real model

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...

python eval.py --runs 5
python judge_flip.py --n 20 --model <judge-model>
```

Both scripts default to `claude-sonnet-4-6`. Change it with `--model`, or set `EVAL_MODEL` / `JUDGE_MODEL`. Each script has **one function to swap** for your own provider: `call_model` in `eval.py`, `call_judge` in `judge_flip.py`.

`judge_flip.py` only sends `--temperature` when you pass it, because newer Claude models (4.7 and later) reject a non-default temperature ([model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)).

### Jev

```bash
pip install deepeval typesafe-sdk
export TYPESAFE_API_KEY=...
python jev_examples.py
```

Jev is in early access. The example was checked against `deepeval` 4.3.2 and `typesafe-sdk` 0.7.5; see the [JevEval docs](https://deepeval.com/docs/metrics-jev-eval) if a newer release changes the API.

## Use it in CI

`eval.py` exits with code 1 when accuracy falls below `--threshold` (default 0.80), so any CI system can gate on it. The included GitHub Actions workflow runs the harness tests and a seeded mock gate. Unseeded, the mock passes or fails by luck, which is exactly why one run is not a result. To gate on a real model, add `ANTHROPIC_API_KEY` as a repository secret and follow the comment at the top of the workflow.

## Make it yours

The code is generic. The value is in `dataset.jsonl`.

1. Replace the rows with 20 or so examples from your real traffic, labeled by hand. Start with the failures you have already seen.
2. Cover every label, including the rare ones. This sample never uses `other`, so it cannot tell you whether the model over-predicts it.
3. Keep a held-out set you never tune prompts on.
4. Change `CATEGORIES`, `PRIORITIES` and `PROMPT` in `eval.py` to match your task. `load_dataset` rejects any gold label outside the schema, so a typo fails loudly instead of quietly capping your accuracy.
5. Run with `--runs 5` before and after every change. If the difference is smaller than the spread, you have not shown anything yet.

Each row looks like this:

```json
{"message": "I was charged twice for my subscription this month", "label": {"category": "billing", "priority": "high"}}
```

## Tests

```bash
pip install pytest
python -m pytest
```

## References

**Why eval**
- He and Thinking Machines Lab (2025). [Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/).
- Sclar et al. (2024). [Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design](https://arxiv.org/abs/2310.11324). ICLR.
- Chen, Zaharia and Zou (2024). How Is ChatGPT's Behavior Changing over Time? Harvard Data Science Review. [arXiv:2307.09009](https://arxiv.org/abs/2307.09009)

**Benchmarks and contamination**
- Akhtar et al. (2026). [When AI Benchmarks Plateau: A Systematic Study of Benchmark Saturation](https://arxiv.org/abs/2602.16763). ICML.
- White et al. (2025). [LiveBench: A Challenging, Contamination-Limited LLM Benchmark](https://arxiv.org/abs/2406.19314). ICLR.
- Touvron et al. (2023). [Llama 2: Open Foundation and Fine-Tuned Chat Models](https://arxiv.org/abs/2307.09288).
- Li et al. (2024). [An Open-Source Data Contamination Report for Large Language Models](https://arxiv.org/abs/2310.17589). EMNLP Findings.
- Xu et al. (2024). [Benchmark Data Contamination of Large Language Models: A Survey](https://arxiv.org/abs/2406.04244).
- Singh et al. (2024). [Evaluation Data Contamination in LLMs](https://arxiv.org/abs/2411.03923).

**Judges**
- Zheng et al. (2023). [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685). NeurIPS.
- Thakur et al. (2025). [Judging the Judges](https://arxiv.org/abs/2406.12624). GEM Workshop, ACL.
- Kasner et al. (2026). [LLMs as Span Annotators](https://arxiv.org/abs/2504.08697).

**Agents**
- Yehudai et al. (2025). [Survey on Evaluation of LLM-based Agents](https://arxiv.org/abs/2503.16416).
- Bandi et al. (2026). [MCP-Atlas: A Large-Scale Benchmark for Tool-Use Competency with Real MCP Servers](https://arxiv.org/abs/2602.00933).
- Li et al. (2025). [The Tool Decathlon](https://arxiv.org/abs/2510.25726). ICLR 2026.

**Multilingual**
- Ahuja et al. (2023). [MEGA: Multilingual Evaluation of Generative AI](https://arxiv.org/abs/2303.12528). EMNLP.
- Ahuja et al. (2024). [MEGAVERSE](https://arxiv.org/abs/2311.07463). NAACL.

**Jev**
- TypeSafe (2026). Introducing System One Models and Jev. typesafe.ai/blog
- Li et al. (2026). [JEV-as-a-Judge: Accept When Confident, Escalate When Unsure](https://arxiv.org/abs/2609.26550).
- DeepEval. [JevEval metric docs](https://deepeval.com/docs/metrics-jev-eval).

## License

[MIT](LICENSE)
