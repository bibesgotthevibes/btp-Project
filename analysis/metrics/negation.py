"""
analysis/metrics/negation.py
────────────────────────────
Negation preservation for lay rewrites (NegEx-style, lexical):
- negation_dropped: findings negated in the source but only affirmed in the output,
  e.g. "no pneumothorax" -> "there is a pneumothorax". The dangerous direction.
- negation_added: findings affirmed in the source but only negated in the output,
  e.g. "cardiomegaly" -> "no cardiomegaly". Noisier: lay text often phrases abnormal
  findings with "not" ("lungs are not fully inflated" for "low lung volumes").
- negation_shared_terms: findings present in both texts (the denominator).
- negation_cue_retention: negation cues in output / in source. Low values mean
  negative findings ("no effusion") were dropped rather than translated.

ponytail: lexical matching only. A flip is caught when the finding word survives
into the output ("pneumothorax"); paraphrased findings ("collapsed lung") are only
covered by cue retention and by AlignScore. Upgrade path: medspaCy/negspaCy + UMLS.
"""

import re
from typing import Dict, Set, Tuple

NEG_CUES = {"no", "not", "without", "negative", "absent", "absence", "none", "neither", "nor",
            "never", "free", "denies", "cannot", "isn't", "aren't", "doesn't", "don't", "didn't"}
# Words that end a negation's scope ("no effusion but small nodule": nodule is affirmed).
SCOPE_BREAKS = {"but", "however", "although", "though", "except", "which", "whereas", "yet"}
WINDOW = 8  # tokens after a cue that stay negated; lay text is wordier than NegEx's ~5-6 assumes
# Too generic to count as a finding.
STOP = {"there", "these", "those", "which", "evidence", "signs", "change", "changes", "focal", "acute",
        "noted", "seen", "present", "identified", "appear", "appears", "visible", "study", "image",
        "images", "examination", "other", "about", "their", "would", "could", "should", "being",
        "large", "small", "chest", "typical", "space", "finding", "suspicious", "significant"}

# "no fluid, a condition called pleural effusion": the term is being named, not asserted.
NAMING = {"called", "termed", "named", "known"}

_SENT = re.compile(r"(?<=[.!?;])\s+|\n+")
_TOK = re.compile(r"[a-z]+(?:'[a-z]+)?")


def _key(word: str) -> str:
    """Singularize: opacities->opacity, effusions->effusion (prefix stems merged pneumonia/pneumothorax)."""
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("sses", "xes")):  # masses->mass
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us")):  # keep suspicious, process
        return word[:-1]
    return word


def _polarities(text: str) -> Tuple[Dict[str, Set[str]], int]:
    """Map each finding stem to the polarities it occurs with ('neg'/'pos'); count cues."""
    pol: Dict[str, Set[str]] = {}
    cues = 0
    # Bracketed glosses restate the phrase before them ("no fluid around the lungs (pleural
    # effusion)"); their terms sit outside the negation window, so drop them.
    text = re.sub(r"\([^)]*\)", " ", text)
    for sent in _SENT.split(text.lower()):
        toks = _TOK.findall(sent)
        last_cue = None
        for i, t in enumerate(toks):
            if t in NEG_CUES:
                cues += 1
                last_cue = i
                continue
            if t in SCOPE_BREAKS:
                last_cue = None
                continue
            t = _key(t)
            if len(t) < 5 or t in STOP or NAMING & set(toks[max(0, i - 3):i]):
                continue
            negated = last_cue is not None and i - last_cue <= WINDOW
            pol.setdefault(t, set()).add("neg" if negated else "pos")
    return pol, cues


def compute_negation_metrics(source_text: str, generated_text: str) -> Dict[str, float]:
    src_pol, src_cues = _polarities(source_text)
    gen_pol, gen_cues = _polarities(generated_text)
    shared = src_pol.keys() & gen_pol.keys()
    # A flip = the two texts never agree on this finding's polarity.
    flipped = [k for k in shared if not (src_pol[k] & gen_pol[k])]
    return {
        "negation_dropped": sum(1 for k in flipped if "neg" in src_pol[k]),
        "negation_added": sum(1 for k in flipped if "pos" in src_pol[k]),
        "negation_shared_terms": len(shared),
        "negation_cue_retention": round(gen_cues / src_cues, 3) if src_cues else 1.0,
    }


if __name__ == "__main__":
    src = "The lungs are clear. There is no pneumothorax or pleural effusion. Mild cardiomegaly."
    ok = compute_negation_metrics(src, "Your lungs are clear. There is no pneumothorax or pleural effusion. "
                                       "The heart is mildly enlarged (cardiomegaly).")
    assert ok["negation_dropped"] == ok["negation_added"] == 0 and ok["negation_cue_retention"] == 1.0, ok
    bad = compute_negation_metrics(src, "There is a pneumothorax. The lungs are clear.")
    assert bad["negation_dropped"] == 1 and bad["negation_added"] == 0, bad
    assert bad["negation_cue_retention"] == 0.0, bad
    rev = compute_negation_metrics(src, "There is no cardiomegaly and no pneumothorax.")
    assert rev["negation_added"] == 1 and rev["negation_dropped"] == 0, rev
    scope = compute_negation_metrics("No effusion but a small nodule.", "No effusion, but there is a small nodule.")
    assert scope["negation_dropped"] == scope["negation_added"] == 0, scope
    named = compute_negation_metrics("No pneumothorax.", "There is no air trapped around your lungs, a condition called pneumothorax.")
    assert named["negation_dropped"] == 0, named
    gloss = compute_negation_metrics("No pleural effusion.", "There is no fluid around the lungs on either side (pleural effusion).")
    assert gloss["negation_dropped"] == 0, gloss
    print("negation self-check passed")
