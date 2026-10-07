# Datasets & Report Sources 📁

This directory contains the clinical datasets and medical reports (pathology, radiology, and discharge summaries) curated and utilized for training, fine-tuning, and evaluating medical text simplification and report generation models.

---

## Directory Overview

```
datasets/
├── README.md
├── discharge_summaries/
│   └── anotated_dataset_v2.xlsx
├── lay_reference_datasets/         # downloaded sets WITH lay-language ground truth
│   ├── plaba/                      # PLABA abstracts + expert adaptations, TREC 2024 term data
│   └── radiology/                  # LaymanRRG_opensource/, LaymanRRG_report_level/, openi_lay_pairs.csv
├── pathology_reports/
│   ├── TCGA-242/
│   │   └── PRAD_reports_eng.xlsx
│   └── TCGA_Reports/
│       └── TCGA_Reports.csv
└── radiology_reports/
    ├── MR-RATE/
    │   ├── batch00_reports.csv ... batch27_reports.csv
    ├── NLMCXR_reports/
    │   └── ecgen-radiology/
    ├── kaggle_saadaldoaij_radiologists/
    │   └── ReportsDATASET.csv
    ├── radiology-report-generation-models-evaluation-dataset-for-chest-x-rays-radevalx-1.0.0/
    │   ├── RadEval_clinically_significant_errors.csv
    │   ├── RadEval-clinically_insignificant_errors.csv
    │   └── metrcis_scores_m2tr.csv
    └── rexerr-v1-clinically-meaningful-chest-x-ray-report-errors-derived-from-mimic-cxr-1.0.0/
        ├── clinician-review.csv
        ├── ReXErr-report-level/
        └── ReXErr-sentence-level/
```

---

## Dataset Catalog & Source Links

### 1. Pathology Reports

| Dataset | Source / Reference | Description & Format |
|---|---|---|
| **TCGA-242** | [Zenodo (Record 20263897)](https://zenodo.org/records/20263897) | Clinical & pathology diagnostic reports from The Cancer Genome Atlas (Prostate Adenocarcinoma `PRAD_reports_eng.xlsx`). |
| **TCGA Reports** | [Mendeley Data](https://data.mendeley.com/datasets/hyg5xkznpx/1?utm_source=chatgpt.com) | Tabulated TCGA clinical pathology reports (`TCGA_Reports.csv`) covering multi-cancer types. |

---

### 2. Radiology Reports

| Dataset | Source / Reference | Description & Format |
|---|---|---|
| **MR-RATE** | [Hugging Face (Forithmus/MR-RATE)](https://huggingface.co/datasets/Forithmus/MR-RATE) | Multi-modal brain & cranial MRI dataset. Contains 28 report batches (`batch00_reports.csv` to `batch27_reports.csv`) with study UID, technique, findings, and clinical impression sections. |
| **ReXErr-v1** (v1.0.0) | [PhysioNet (ReXErr-v1)](https://physionet.org/content/rexerr-v1/1.0.0/) | *Clinically Meaningful Chest X-ray Report Errors Derived from MIMIC-CXR*. Expert-annotated sentence- and report-level clinical error taxonomy and clinician reviews. |
| **RadEval-X** (v1.0.0) | [PhysioNet (RadEval-X)](https://physionet.org/content/rad-eval-x/1.0.0/) | *Radiology Report Generation Models Evaluation Dataset for Chest X-Rays*. Benchmark dataset annotated with clinically significant and insignificant error labels. |
| **Radiologists Reports** | [Kaggle (saadaldoaij/radiologists-reports)](https://www.kaggle.com/datasets/saadaldoaij/radiologists-reports) | Curated collection of anonymized clinical radiology reports (`ReportsDATASET.csv`) covering diagnostic imaging modalities. |
| **NLM-CXR / Open-i** | [National Library of Medicine (Open-i)](https://openi.nlm.nih.gov/faq?download=true) | Indiana University Chest X-Ray Collection (`ecgen-radiology`), providing paired radiological text (indications, findings, impressions) and images. |

| **LaymanRRG (BioLaySumm 2025, open track)** | [HF BioLaySumm/BioLaySumm2025-LaymanRRG-opensource-track](https://huggingface.co/datasets/BioLaySumm/BioLaySumm2025-LaymanRRG-opensource-track) | 171k report→lay pairs (PadChest, BIMCV-COVID19, Open-i). Test split lay text is hidden (empty). |
| **LaymanRRG report-level** | [HF LaymanRRG/LaymanRRG-report-level](https://huggingface.co/datasets/LaymanRRG/LaymanRRG-report-level) | 50k MIMIC-CXR lay reports; join to source by `study_id` (needs MIMIC-CXR access). |
| **openi_lay_pairs.csv** | Derived | 2,377 NLMCXR reports (findings/impression) joined to LaymanRRG lay references by image id. |

---

### 3. Discharge Summaries

| Dataset | Source / Reference | Description & Format |
|---|---|---|
| **Annotated Discharge Summaries (v2)** | N/A | 200 clinical discharge summaries (`anotated_dataset_v2.xlsx`) with original clinical narratives, English translations, primary/secondary ICD-10 diagnostic codes, patient outcomes, ICU indicators, and length of stay. Also includes sheets for clinical abbreviation mappings (301 entries) and ICD diagnostic codes. |

---

### 4. Biomedical Plain Language (reference sets)

| Dataset | Source / Reference | Description & Format |
|---|---|---|
| **PLABA** | [OSF rnpmf](https://osf.io/rnpmf/) · [paper](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9811873/) | 749 PubMed abstracts, 919 expert sentence-aligned adaptations (7.6k sentences). |
| **TREC 2024 PLABA** | [trec.nist.gov/data/plaba2024.html](https://trec.nist.gov/data/plaba2024.html) | Task 1: expert terms + replacement type (SUBSTITUTE/EXPLAIN/GENERALIZE/EXEMPLIFY/OMIT) + replacement text for 100 abstracts. Task 2: test sources. |

---

## Notes on Access & Licensing

- **Large File Storage (Git LFS):** All large tabular CSV and Excel datasets in this directory are tracked using Git LFS to keep the repository lightweight.
- **Data Governance & HIPAA:** All datasets are de-identified under respective institutional IRB protocols and data use agreements (DUAs). Ensure compliance with PhysioNet Credentialed Data Use Agreements (for MIMIC derivatives like ReXErr-v1) and Open-i / TCGA open research guidelines.
