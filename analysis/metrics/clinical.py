"""
analysis/metrics/clinical.py
────────────────────────────
Clinical metrics used by BioLaySumm 2025 (radiology task), comparing an output with its reference:
- CheXbert: labels 14 chest X-ray observations (CheXpert classes) as positive in each text.
  Per output we store the positive labels; the summary computes corpus-level micro-F1 over the
  14 classes per model/strategy (as f1chexbert does). chexbert_f1 is a per-output F1 for reference.
- RadGraph F1 (partial reward): overlap of extracted clinical entities and relations.

Both packages were written for transformers 4.x; two tokenizer methods they call were removed in
transformers 5. _install_tokenizer_compat() restores them with the same behaviour.
Checkpoints: CheXbert from huggingface StanfordAIMI/RRG_scorers (chexbert.pth, in the f1chexbert
cache dir); RadGraph downloads its own model on first use.
"""

from functools import lru_cache
from typing import Dict, List

CHEXPERT_CLASSES = ["Enlarged Cardiomediastinum", "Cardiomegaly", "Lung Opacity", "Lung Lesion", "Edema",
                    "Consolidation", "Pneumonia", "Atelectasis", "Pneumothorax", "Pleural Effusion",
                    "Pleural Other", "Fracture", "Support Devices", "No Finding"]


def _install_tokenizer_compat():
    import torch
    import transformers
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase as Base
    transformers.AdamW = getattr(transformers, "AdamW", torch.optim.AdamW)

    def encode_plus(self, text, text_pair=None, add_special_tokens=True, **kw):
        # transformers 4.x accepted an already-split token list and converted it to ids (f1chexbert relies on this)
        if isinstance(text, (list, tuple)) and text_pair is None and text and all(isinstance(t, str) for t in text):
            ids = self.convert_tokens_to_ids(list(text))
            return {"input_ids": self.build_inputs_with_special_tokens(ids) if add_special_tokens else ids}
        return self(text, text_pair=text_pair, add_special_tokens=add_special_tokens, **kw)

    def build_inputs_with_special_tokens(self, a, b=None):  # BERT layout: [CLS] a [SEP] (b [SEP])
        return [self.cls_token_id] + a + [self.sep_token_id] + ((b + [self.sep_token_id]) if b else [])

    for name, fn in [("encode_plus", encode_plus), ("build_inputs_with_special_tokens", build_inputs_with_special_tokens)]:
        if name not in Base.__dict__:
            setattr(Base, name, fn)


def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"


@lru_cache(maxsize=1)
def _chexbert():
    _install_tokenizer_compat()
    from f1chexbert import F1CheXbert  # fail loudly if missing
    return F1CheXbert(device=_device())


@lru_cache(maxsize=1)
def _radgraph():
    _install_tokenizer_compat()
    from radgraph import F1RadGraph  # fail loudly if missing
    return F1RadGraph(reward_level="partial", model_type="radgraph")


def chexbert_positives(text: str) -> List[str]:
    labels = _chexbert().get_label(text)
    return [c for c, v in zip(CHEXPERT_CLASSES, labels) if v == 1]


def compute_clinical_metrics(reference_text: str, generated_text: str) -> Dict[str, object]:
    if not reference_text.strip() or not generated_text.strip():
        return {"chexbert_f1": 0.0, "chexbert_out": "", "chexbert_ref": "", "radgraph_f1": 0.0}
    out, ref = set(chexbert_positives(generated_text)), set(chexbert_positives(reference_text))
    tp = len(out & ref)
    f1 = 1.0 if not out and not ref else (2 * tp / (len(out) + len(ref)))
    rg_mean, _, _, _ = _radgraph()(hyps=[generated_text], refs=[reference_text])
    return {"chexbert_f1": round(f1 * 100.0, 2), "chexbert_out": ";".join(sorted(out)), "chexbert_ref": ";".join(sorted(ref)),
            "radgraph_f1": round(float(rg_mean) * 100.0, 2)}


def corpus_chexbert_f1(pairs) -> float:
    """Micro-F1 over the 14 CheXpert classes for a list of (chexbert_out, chexbert_ref) label strings."""
    tp = fp = fn = 0
    for o, r in pairs:
        o, r = set(filter(None, (o or "").split(";"))), set(filter(None, (r or "").split(";")))
        tp += len(o & r); fp += len(o - r); fn += len(r - o)
    return round(200.0 * tp / (2 * tp + fp + fn), 2) if tp else 0.0


if __name__ == "__main__":
    ref = "There is a small amount of fluid around the left lung. There is no air outside the lungs. The heart is bigger than normal."
    good = "There is a little fluid around the left lung. No air has leaked outside the lungs. The heart is larger than usual."
    bad = "The lungs look clear with no fluid. There is air outside the lungs. The heart is a normal size."
    g, b = compute_clinical_metrics(ref, good), compute_clinical_metrics(ref, bad)
    assert g["chexbert_ref"] == "Cardiomegaly;Pleural Effusion", g
    assert g["chexbert_f1"] > b["chexbert_f1"] and g["radgraph_f1"] > b["radgraph_f1"], (g, b)
    assert corpus_chexbert_f1([("A;B", "A;B"), ("", "C")]) == 80.0
    print("clinical self-check passed", g, b)
