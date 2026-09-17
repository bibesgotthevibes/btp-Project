# Comparative Analysis & Benchmark Summary Report

**Total Records**: 5 | **Successfully Scored**: 5

## 1. Model Comparison Leaderboard

| Model | Task | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-1 | BERTScore | SBERT Cos | Jargon Red % | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|
| **gemini/3.1pro** | simplification | 11.43 | 56.55 | 2.97 | 22.7% | 47.56% | 45.0% | 75.16% | 32.13s |

---

## 2. Task Comparison: Simplification vs. Summarization

| Task | Avg FKGL | Avg FRE | Complex Words % | Avg Word Len | SARI | Comp (Words) | Par Explanations/100w |
|---|---|---|---|---|---|---|---|
| **Simplification** | 11.43 | 56.55 | 63.46% | 4.78 | 2.97 | 0.26x | 5.15 |

---

## 3. Datatype Performance Comparison

| Datatype | Task | Samples | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-L | Jargon Red % |
|---|---|---|---|---|---|---|---|
| **Discharge** | simplification | 5 | 11.43 | 56.55 | 2.97 | 22.7% | 75.16% |

---

## 4. Prompt Strategy: Zero-Shot vs. Few-Shot

| Strategy | Task | SARI (↑) | Par Explanations/100w | ROUGE-1 | FKGL (↓) | FRE (↑) |
|---|---|---|---|---|---|---|
| **few-shot** | simplification | 2.97 | 5.15 | 22.7% | 11.43 | 56.55 |