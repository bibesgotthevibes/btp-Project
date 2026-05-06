import pandas as pd

res = pd.read_excel("results_1/lay_english_pipeline_output.xlsx")

# How many outputs start with <2en>?
starts_2en = res["indian_lay_english"].str.startswith("<2en>").sum()
print(f"Outputs starting with <2en>: {starts_2en}/{len(res)}")

has_study = res["indian_lay_english"].str.contains("this study", case=False, na=False).sum()
print(f"Contains 'this study' (hallucination): {has_study}")

has_she = res["indian_lay_english"].str.contains("she ", case=False, na=False).sum()
print(f"Contains 'she' (gender hallucination): {has_she}")

# Entity preservation check: count disease names in original vs output
test_terms = ["crohn", "sepsis", "pneumonia", "diabetes", "epileptic", "amputation",
              "kidney", "anemia", "tuberculosis", "hypertension", "infarction"]
print("\n=== Entity Preservation Check ===")
for term in test_terms:
    in_orig = res["translated discharge_summary"].str.contains(term, case=False, na=False).sum()
    in_output = res["indian_lay_english"].str.contains(term, case=False, na=False).sum()
    in_lay = res["lay_replaced_summary"].str.contains(term, case=False, na=False).sum()
    print(f"  {term:20s}  orig={in_orig:3d}  lay_replaced={in_lay:3d}  model_output={in_output:3d}")

# Check data.tsv
print("\n=== data.tsv (training data) ===")
ft = pd.read_csv("data/data.tsv", sep="\t", nrows=5)
for i in range(3):
    orig = str(ft["original"].iloc[i])[:250]
    simp = str(ft["english simplified"].iloc[i])[:250]
    print(f"\nRow {i}:")
    print(f"  ORIGINAL:   {orig}")
    print(f"  SIMPLIFIED: {simp}")

ft_all = pd.read_csv("data/data.tsv", sep="\t", usecols=["original", "english simplified"], nrows=10000)
ft_all = ft_all.dropna()
orig_lens = ft_all["original"].str.split().str.len()
simp_lens = ft_all["english simplified"].str.split().str.len()
wc = res["word_count_original"]
print(f"\ndata.tsv original avg words:    {orig_lens.mean():.0f}  median: {orig_lens.median():.0f}")
print(f"data.tsv simplified avg words:  {simp_lens.mean():.0f}  median: {simp_lens.median():.0f}")
print(f"Discharge summary avg words:    {wc.mean():.0f}  median: {wc.median():.0f}")

# Check predictions-t5-base.tsv
print("\n=== predictions-t5-base.tsv (reference) ===")
t5 = pd.read_csv("predictions-t5-base.tsv", sep="\t", nrows=3)
print(f"Columns: {list(t5.columns)}")
for i in range(2):
    for col in t5.columns[:3]:
        print(f"  Row {i} {col}: {str(t5[col].iloc[i])[:200]}")
    print()

# Row 0: detailed comparison
print("\n=== ROW 0 DETAILED ===")
row = res.iloc[0]
print("ORIGINAL (first 600 chars):")
print(str(row["translated discharge_summary"])[:600])
print("\nMODEL OUTPUT (first 600 chars):")
print(str(row["indian_lay_english"])[:600])
print(f"\nOriginal words: {len(str(row['translated discharge_summary']).split())}")
print(f"Output words: {len(str(row['indian_lay_english']).split())}")
