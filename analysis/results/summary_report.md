# Comparative Analysis & Benchmark Summary Report

**Total Records**: 44 | **Successfully Scored**: 44

## 1. Model Comparison Leaderboard

| Model | Task | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-1 | BERTScore | SBERT Cos | Jargon Red % | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|
| **cerebras/gptoss** | simplification | 11.76 | 50.95 | 14.21 | 58.49% | 69.31% | 72.96% | -9.1% | 4.33s |
| **cerebras/gptoss** | summarization | 10.28 | 35.44 | 10.44 | 49.71% | 46.52% | 51.94% | -171.43% | 2.05s |
| **cerebras/qwen3.8** | simplification | 10.89 | 47.39 | 13.38 | 56.64% | 70.88% | 77.42% | 30.58% | 1.97s |
| **cerebras/qwen3.8** | summarization | 14.08 | 10.75 | 12.99 | 58.67% | 65.82% | 57.35% | -100.0% | 1.72s |
| **gemini/3.1pro** | simplification | 11.2 | 54.88 | 8.71 | 39.95% | 54.52% | 57.38% | 43.47% | 22.22s |
| **gemini/3.1pro** | summarization | 15.41 | 8.02 | 12.94 | 55.94% | 62.45% | 72.87% | -100.0% | 9.01s |
| **gemini/3.8flash** | simplification | 11.49 | 49.54 | 13.91 | 56.57% | 64.89% | 72.83% | 9.06% | 10.35s |
| **gemini/3.8flash** | summarization | 14.47 | 23.09 | 14.53 | 61.59% | 73.89% | 75.92% | -42.86% | 8.64s |

---

## 2. Task Comparison: Simplification vs. Summarization

| Task | Avg FKGL | Avg FRE | Complex Words % | Avg Word Len | SARI | Comp (Words) | Par Explanations/100w |
|---|---|---|---|---|---|---|---|
| **Simplification** | 11.34 | 50.69 | 62.14% | 4.98 | 12.55 | 1.3x | 5.28 |
| **Summarization** | 13.56 | 19.32 | 76.83% | 6.25 | 12.72 | 1.22x | 2.4 |

---

## 3. Datatype Performance Comparison

| Datatype | Task | Samples | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-L | Jargon Red % |
|---|---|---|---|---|---|---|---|
| **Discharge** | simplification | 40 | 11.34 | 50.69 | 12.55 | 52.91% | 18.5% |
| **Discharge** | summarization | 4 | 13.56 | 19.32 | 12.72 | 56.48% | -103.57% |

---

## 4. Prompt Strategy: Zero-Shot vs. Few-Shot

| Strategy | Task | SARI (↑) | Par Explanations/100w | ROUGE-1 | FKGL (↓) | FRE (↑) |
|---|---|---|---|---|---|---|
| **few-shot** | simplification | 10.96 | 5.63 | 48.66% | 11.94 | 48.39 |
| **zero-shot** | simplification | 14.15 | 4.93 | 57.17% | 10.73 | 52.99 |
| **zero-shot** | summarization | 12.72 | 2.4 | 56.48% | 13.56 | 19.32 |