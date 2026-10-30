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

---

## Türkçe

**AI Connect Istanbul** (30 Eylül 2026) konuşmam "Your LLM Evaluation Is Lying to You" için hazırlanmış eşlik kodu. LLM değerlendirmelerinin (eval) sizi nasıl yanılttığını ve bunu yakalayan ucuz alışkanlıkları gösteren küçük, okunabilir betikler.

Tüm betikler `--mock` ile saniyeler içinde çalışır, API anahtarı gerekmez.

### Tek tabloda konuşma

| Yalan | Neden yanlış | Çözüm | Bu repoda |
| --- | --- | --- | --- |
| "Benchmark'ta büyük modeli geçiyor." | Doygunluk (saturation) ve veri kirlenmesi (contamination) | Kirlenmeden arındırıldığında ne kaldığını sorun; kendi hatalarınızdan 20 örnek oluşturun | `dataset.jsonl` |
| "LLM hakemi iyileştiğini söyledi." | Hakemlerin konum, uzunluk ve kendini kayırma eğilimleri vardır | İnsan etiketleriyle kalibre edin, cevap sırasını rastgele yapın | `judge_flip.py` |
| "Ajanım çalışıyor. Tüm araçları çağırdı." | Doğru çağrılar yapılsa bile görev başarısız olabilir | Tüm süreci (trajectory) puanlayın | `jev_examples.py` (araç hata yönetimi) |
| "Çalışıyor." | Küçük örneklem, tek çalıştırma, sadece İngilizce | Ayrılmış test seti, birden çok çalıştırma, hizmet verdiğiniz dilleri test edin | `eval.py --runs 5` |

### İçerik

- `eval.py` + `dataset.jsonl`: Tek bir yetenek (destek talebi yönlendirme) için eksiksiz bir eval. Deterministik puanlayıcı, hata nedenleri, CI kapısı ve gürültü tabanını gösteren `--runs` seçeneği.
- `judge_flip.py`: LLM hakeminde konum yanlılığı. Aynı iki cevap, sırayı değiştirin, kararları sayın.
- `jev_examples.py`: DeepEval `JevEval` metrikleri olarak Jev soruları (Noul, Score, Choice); Türkçe bir RAG kontrolü dahil.
- `tests/`: Altyapının kendisi için testler: ayrıştırıcı, puanlayıcı, şema kontrolleri, kapı çıkış kodları.
- `.github/workflows/eval.yml`: Her push'ta testleri ve eval kapısını çalıştırır.

### Hızlı başlangıç (API anahtarı olmadan)

Python 3.10 veya üstü gerekir. Mock komutları yalnızca standart kütüphaneyi kullanır. Komutlar için yukarıdaki [Quick start](#quick-start-no-api-key) bölümüne bakın.

`--mock`, her etkiyi hemen görebilmeniz için gerçek model yerine simüle edilmiş bir model kullanır. Mock sayıları etkiyi göstermek içindir; herhangi bir gerçek model hakkında sonuç değildir. `--seed` mock çıktısını tekrarlanabilir yapar.

**Ne görmelisiniz:**

- Tek bir çalıştırma size skoru **ve her örneğin neden başarısız olduğunu** söyler.
- Aynı model, aynı veri üzerinde beş kez çalıştırıldığında skor %73 ile %93 arasında oynar. Bu aralıktan küçük bir fark sonuç değil, varyanstır.
- Hakem, yalnızca cevap sırası değiştirildiğinde ilk sıradaki cevabı çok daha sık seçer. Sıraya duyarsız bir hakem %50 civarında olmalıdır.

`python judge_flip.py --mock --seed 0` deneyin: sıra başına yalnızca 10 denemeyle aynı yanlı hakem yansız görünebilir. Bu yine gürültü dersidir. Hakeminiz hakkında bir sonuca varmadan önce `--n 50` veya daha fazlasını kullanın.

### Gerçek bir modelle

`pip install -r requirements.txt` ile bağımlılıkları kurun ve `ANTHROPIC_API_KEY` ortam değişkenini ayarlayın. Her iki betik de varsayılan olarak `claude-sonnet-4-6` kullanır; `--model` ile ya da `EVAL_MODEL` / `JUDGE_MODEL` ortam değişkenleriyle değiştirebilirsiniz. Kendi sağlayıcınızı kullanmak için her betikte **değiştirmeniz gereken tek bir fonksiyon** var: `eval.py` içinde `call_model`, `judge_flip.py` içinde `call_judge`.

`judge_flip.py`, `--temperature` değerini yalnızca siz verdiğinizde gönderir, çünkü yeni Claude modelleri (4.7 ve sonrası) varsayılan dışı bir temperature değerini reddeder.

Jev şu an erken erişimdedir. Örnek `deepeval` 4.3.2 ve `typesafe-sdk` 0.7.5 ile test edildi; yeni bir sürüm API'yi değiştirirse [JevEval dokümanlarına](https://deepeval.com/docs/metrics-jev-eval) bakın.

### CI'da kullanım

`eval.py`, doğruluk `--threshold` değerinin (varsayılan 0.80) altına düştüğünde 1 çıkış koduyla sonlanır, böylece herhangi bir CI sistemi buna göre kapı koyabilir. Dahil edilen GitHub Actions iş akışı, altyapı testlerini ve seed'li bir mock kapısını çalıştırır. Seed olmadan mock şans eseri geçer ya da kalır; tek bir çalıştırmanın neden sonuç olmadığını tam da bu gösterir. Gerçek bir modelle kapı koymak için `ANTHROPIC_API_KEY`'i repo secret'ı olarak ekleyin ve iş akışı dosyasının başındaki yorumu takip edin.

### Kendinize uyarlayın

Kod geneldir. Asıl değer `dataset.jsonl` içindedir.

1. Satırları gerçek trafiğinizden alınmış, elle etiketlenmiş 20 kadar örnekle değiştirin. Daha önce gördüğünüz hatalarla başlayın.
2. Nadir olanlar dahil her etiketi kapsayın. Bu örnek veri `other` etiketini hiç kullanmıyor, bu yüzden modelin onu fazla tahmin edip etmediğini söyleyemez.
3. Prompt'larınızı asla üzerinde ayarlamadığınız ayrı bir test seti tutun.
4. `eval.py` içindeki `CATEGORIES`, `PRIORITIES` ve `PROMPT` değerlerini görevinize göre değiştirin. `load_dataset`, şema dışındaki her etiketi reddeder; böylece bir yazım hatası doğruluğunuzu sessizce düşürmek yerine açıkça hata verir.
5. Her değişiklikten önce ve sonra `--runs 5` ile çalıştırın. Fark, dağılımdan küçükse henüz hiçbir şey göstermiş değilsiniz.
