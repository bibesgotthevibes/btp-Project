# Comparative Analysis & Benchmark Summary Report

**Total Records**: 8 | **Successfully Scored**: 8

## 1. Model Comparison Leaderboard

| Model | Task | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-1 | BERTScore | SBERT Cos | Jargon Red % | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|
| **cerebras/gptoss** | simplification | 2.98 | 86.95 | 22.36 | 53.18% | 16.6% | 21.87% | -114.29% | 2.97s |
| **cerebras/gptoss** | summarization | 10.28 | 35.44 | 10.44 | 49.71% | 46.52% | 51.94% | -171.43% | 2.05s |
| **cerebras/qwen3.8** | simplification | 12.5 | 38.87 | 22.68 | 64.95% | 70.11% | 73.44% | -14.29% | 1.94s |
| **cerebras/qwen3.8** | summarization | 14.08 | 10.75 | 12.99 | 58.67% | 65.82% | 57.35% | -100.0% | 1.72s |
| **gemini/3.1pro** | simplification | 13.72 | 42.41 | 17.19 | 52.51% | 52.78% | 60.22% | -42.86% | 17.3s |
| **gemini/3.1pro** | summarization | 15.41 | 8.02 | 12.94 | 55.94% | 62.45% | 72.87% | -100.0% | 9.01s |
| **gemini/3.8flash** | simplification | 12.51 | 42.12 | 15.91 | 51.61% | 53.5% | 60.61% | -42.86% | 13.57s |
| **gemini/3.8flash** | summarization | 14.47 | 23.09 | 14.53 | 61.59% | 73.89% | 75.92% | -42.86% | 8.64s |

---

## 2. Task Comparison: Simplification vs. Summarization

| Task | Avg FKGL | Avg FRE | Complex Words % | Avg Word Len | SARI | Comp (Words) | Par Explanations/100w |
|---|---|---|---|---|---|---|---|
| **Simplification** | 10.43 | 52.59 | 61.59% | 4.94 | 19.54 | 3.26x | 3.25 |
| **Summarization** | 13.56 | 19.32 | 76.83% | 6.25 | 12.72 | 1.22x | 2.4 |

---

## 3. Datatype Performance Comparison

| Datatype | Task | Samples | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-L | Jargon Red % |
|---|---|---|---|---|---|---|---|
| **Discharge** | simplification | 4 | 10.43 | 52.59 | 19.54 | 55.56% | -53.57% |
| **Discharge** | summarization | 4 | 13.56 | 19.32 | 12.72 | 56.48% | -103.57% |

---

## 4. Prompt Strategy: Zero-Shot vs. Few-Shot

| Strategy | Task | SARI (↑) | Par Explanations/100w | ROUGE-1 | FKGL (↓) | FRE (↑) |
|---|---|---|---|---|---|---|
| **zero-shot** | simplification | 19.54 | 3.25 | 55.56% | 10.43 | 52.59 |
| **zero-shot** | summarization | 12.72 | 2.4 | 56.48% | 13.56 | 19.32 |