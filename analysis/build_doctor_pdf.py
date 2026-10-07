"""
analysis/build_doctor_pdf.py
────────────────────────────
Builds a clinician review pack: each original report followed by its usable
simplified versions, with a short review form after each version. No scores.

Versions are blinded (labelled A, B, C… in a fixed random order per report) so
the reviewer is not influenced by model names. The key is written separately.

Outputs:
  results/doctor_review_pack.pdf
  results/doctor_review_key.csv   (version letter -> model / strategy; keep for yourself)

Run: python analysis/build_doctor_pdf.py
"""

import sys
import csv
import json
import random
from pathlib import Path
from xml.sax.saxutils import escape

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Flowable, CondPageBreak,
)

from analysis.config import RESULTS_DIR, MODEL_ENDPOINTS

OUT_PDF = RESULTS_DIR / "doctor_review_pack.pdf"
OUT_KEY = RESULTS_DIR / "doctor_review_key.csv"

FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Body", str(FONT_DIR / "calibri.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(FONT_DIR / "calibrib.ttf")))
pdfmetrics.registerFont(TTFont("Body-Italic", str(FONT_DIR / "calibrii.ttf")))
pdfmetrics.registerFont(TTFont("Sym", str(FONT_DIR / "seguisym.ttf")))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")
BODY_GLYPHS = set(pdfmetrics.getFont("Body").face.charToGlyph)

INK = colors.HexColor("#17222b")
MUTED = colors.HexColor("#5a6975")
ACCENT = colors.HexColor("#1d5c73")
TINT = colors.HexColor("#eef4f6")
RULE = colors.HexColor("#c9d3d9")

TYPE_LABEL = {"discharge": "Discharge summary", "pathology": "Pathology report", "radiology": "Radiology report (MRI)"}
MODEL_NAMES = {"gemini/3.8flash": "Gemini 3.8 Flash", "gemini/3.1pro": "Gemini 3.1 Pro", "cerebras/gptoss": "GPT-OSS", "cerebras/qwen3.8": "Qwen 3.8"}

S = {
    "title": ParagraphStyle("title", fontName="Body-Bold", fontSize=22, leading=27, textColor=INK, spaceAfter=6),
    "subtitle": ParagraphStyle("subtitle", fontName="Body", fontSize=12, leading=16, textColor=MUTED, spaceAfter=18),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=16, leading=20, textColor=INK, spaceAfter=2),
    "kicker": ParagraphStyle("kicker", fontName="Body-Bold", fontSize=8.5, leading=11, textColor=ACCENT, spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=12.5, leading=16, textColor=ACCENT, spaceBefore=6, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10.5, leading=14.6, textColor=INK, spaceAfter=7, alignment=TA_LEFT),
    "source": ParagraphStyle("source", fontName="Body", fontSize=9.6, leading=13, textColor=INK, spaceAfter=5, leftIndent=8),
    "note": ParagraphStyle("note", fontName="Body-Italic", fontSize=9.5, leading=13, textColor=MUTED, spaceAfter=6),
    "form": ParagraphStyle("form", fontName="Body", fontSize=9.5, leading=13, textColor=INK),
    "formlabel": ParagraphStyle("formlabel", fontName="Body-Bold", fontSize=9.5, leading=13, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=10.5, leading=14.6, textColor=INK, leftIndent=14, bulletIndent=2, spaceAfter=3),
}

BOX = '<font name="Sym">☐</font>'


def txt(s: str) -> str:
    """Escape for Paragraph markup; route glyphs Calibri lacks to the symbol font."""
    s = s.replace("\u2011", "-").replace("\u202f", " ").replace("\u00a0", " ")
    out = []
    for ch in escape(s):
        if ch in "\n\r" or ord(ch) in BODY_GLYPHS:
            out.append(ch)
        else:
            out.append(f'<font name="Sym">{ch}</font>')
    return "".join(out)


def paragraphs(text: str, style, keep_lines=False):
    """Split text into Paragraphs; keep single line breaks for tabular source reports."""
    items = []
    for block in [b.strip() for b in text.replace("\r", "").split("\n\n") if b.strip()]:
        body = txt(block)
        body = body.replace("\n", "<br/>") if keep_lines else " ".join(body.split("\n"))
        items.append(Paragraph(body, style))
    return items


class SectionMarker(Flowable):
    """Zero-size flowable that tells the page footer which report is being shown."""
    def __init__(self, label):
        super().__init__()
        self.label = label
    def wrap(self, *a):
        return (0, 0)
    def draw(self):
        self.canv._section_label = self.label


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 8.5)
    canvas.setFillColor(MUTED)
    label = getattr(canvas, "_section_label", "")
    canvas.drawString(2 * cm, 1.2 * cm, "Simplified medical reports · clinical review" + (f"  ·  {label}" if label else ""))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def review_form(letter: str):
    rows = [
        [Paragraph(f"Review of Version {letter}", S["formlabel"]), ""],
        [Paragraph("Accuracy", S["formlabel"]), Paragraph(f"{BOX} No errors &nbsp;&nbsp; {BOX} Minor errors &nbsp;&nbsp; {BOX} Serious errors", S["form"])],
        [Paragraph("Invented information", S["formlabel"]), Paragraph(f"{BOX} None &nbsp;&nbsp; {BOX} Yes (please note below)", S["form"])],
        [Paragraph("Important information missing", S["formlabel"]), Paragraph(f"{BOX} None &nbsp;&nbsp; {BOX} Yes (please note below)", S["form"])],
        [Paragraph("Easy for a patient or family to understand", S["formlabel"]), Paragraph(f"{BOX} 1 &nbsp; {BOX} 2 &nbsp; {BOX} 3 &nbsp; {BOX} 4 &nbsp; {BOX} 5 &nbsp;&nbsp; <font color='#5a6975'>(1 = very hard, 5 = very easy)</font>", S["form"])],
        [Paragraph("Could this be given to the patient?", S["formlabel"]), Paragraph(f"{BOX} As written &nbsp;&nbsp; {BOX} After edits &nbsp;&nbsp; {BOX} No", S["form"])],
        [Paragraph("What was done well / what was missed or wrong", S["formlabel"]), ""],
        ["", ""], ["", ""], ["", ""],
    ]
    t = Table(rows, colWidths=[6.2 * cm, 10.8 * cm], rowHeights=[None] * 7 + [0.75 * cm] * 3)
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 6), (1, 6)),
        ("SPAN", (0, 7), (1, 7)), ("SPAN", (0, 8), (1, 8)), ("SPAN", (0, 9), (1, 9)),
        ("BACKGROUND", (0, 0), (1, 0), TINT),
        ("BOX", (0, 0), (-1, -1), 0.8, RULE),
        ("LINEBELOW", (0, 0), (-1, 5), 0.4, RULE),
        ("LINEBELOW", (0, 7), (-1, 8), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def load_versions(version_set: str = "qwen-pairs"):
    """version_set: 'qwen-pairs' (Qwen NER-guided + zero-shot per report) or 'all' (every usable version)."""
    records = json.load(open(RESULTS_DIR / "evaluations.json", encoding="utf-8"))
    if version_set == "qwen-pairs":
        records = [r for r in records if r.get("model") == "cerebras/qwen3.8"]
    checks = json.load(open(RESULTS_DIR / "content_retention.json", encoding="utf-8"))["trials"]
    samples = {}
    for r in records:
        if r.get("task") != "simplification":
            continue
        s = samples.setdefault(r["sample_id"], {"id": r["sample_id"], "type": r["datatype"], "source": r["source_text"], "versions": [], "excluded": 0})
        c = checks.get(r["trial_id"])
        if r.get("status") == "success" and c and c.get("valid_output"):
            s["versions"].append(r)
        elif r.get("status") == "success":
            s["excluded"] += 1
    order = {"discharge": 0, "pathology": 1, "radiology": 2}
    return sorted(samples.values(), key=lambda s: (order[s["type"]], s["id"]))


def actual_model(r):
    extra = r.get("extra") or {}
    cfg = MODEL_ENDPOINTS[r["model"]]
    if r.get("model_used"):
        return r["model_used"]
    if extra.get("fallback_used"):
        return cfg["fallback_models"][0]
    if extra.get("fallback_provider") == "groq" or extra.get("routed_to") == "groq":
        # Older records don't store the model; Groq's first candidate is groq_model_id
        return f"groq:{cfg.get('groq_model_id')} (first candidate)"
    return cfg.get("model_id", r["model"])


def main():
    version_set = sys.argv[1] if len(sys.argv) > 1 else "qwen-pairs"
    samples = load_versions(version_set)
    included = [s for s in samples if s["versions"]]
    skipped = [s for s in samples if not s["versions"]]

    doc = BaseDocTemplate(str(OUT_PDF), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.9 * cm, bottomMargin=1.9 * cm,
                          title="Simplified Medical Reports: Clinical Review", author="BTP project")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=footer)])

    story = []
    n_versions = sum(len(s["versions"]) for s in included)
    story += [
        Paragraph("Simplified Medical Reports", S["title"]),
        Paragraph("Clinical review pack: original reports and AI-written plain-language versions", S["subtitle"]),
        Paragraph("Why we are asking", S["h2"]),
        Paragraph(
            "We are testing whether AI language models can rewrite medical reports into plain language that patients and their "
            "families can understand. The models were asked to keep every clinical fact, explain each medical term in simple words, "
            "and write at roughly a 6th-grade reading level in plain Indian English. Your judgement on accuracy and safety is the "
            "part that automatic measures cannot provide.", S["body"]),
        Paragraph("What is in this pack", S["h2"]),
        Paragraph(
            f"{len(included)} original reports (discharge summaries, prostate pathology reports and brain MRI reports), each followed by "
            f"its simplified versions: {n_versions} versions in total. Each version is labelled with a letter (A, B, C…). The letters are "
            "assigned in random order and do not reveal which AI method produced the text, so that each version is judged on its own.", S["body"]),
        Paragraph("For each version, please check", S["h2"]),
    ]
    for item in [
        "<b>Accuracy</b>: is anything wrong, misinterpreted, or placed at the wrong time?",
        "<b>Invented information</b>: does it state anything that is not in the original (for example test values, warning signs, instructions or relationships)?",
        "<b>Missing information</b>: is anything clinically important left out?",
        "<b>Understandability</b>: would a patient or family member follow it?",
        "<b>Suitability</b>: could it be handed to a patient as written, after edits, or not at all?",
    ]:
        story.append(Paragraph(item, S["bullet"], bulletText="•"))
    story += [
        Spacer(1, 6),
        Paragraph("A short review form follows each version. Brief notes are very helpful: they tell us exactly what the models get right and wrong.", S["body"]),
        Paragraph("About the source reports", S["h2"]),
        Paragraph(
            "The reports come from public, de-identified research datasets. Placeholders such as [person], {organization} and {omitted} "
            "are part of the original anonymisation, not errors. The discharge summaries are from a Brazilian hospital dataset "
            "(SUS is Brazil's public health system); the pathology and radiology reports appear to be English translations of "
            "German and Turkish originals, so some wording in the originals is unusual.", S["body"]),
    ]
    if skipped:
        story.append(Paragraph(
            "Not included: " + ", ".join(s["id"] for s in skipped) +
            ". No complete simplified version was produced for these reports (the outputs were cut off), so there is nothing to review.", S["note"]))

    story.append(Paragraph("Contents", S["h2"]))
    toc = [["Report", "Type", "Versions"]] + [[s["id"], TYPE_LABEL[s["type"]], str(len(s["versions"]))] for s in included]
    tt = Table(toc, colWidths=[3 * cm, 9 * cm, 3 * cm])
    tt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Body-Bold", 9.5), ("FONT", (0, 1), (-1, -1), "Body", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK), ("LINEBELOW", (0, 0), (-1, 0), 0.8, RULE),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tt)

    key_rows = []
    for s in included:
        versions = list(s["versions"])
        random.Random(f"review-{s['id']}").shuffle(versions)
        letters = [chr(ord("A") + i) for i in range(len(versions))]

        story += [PageBreak(), SectionMarker(s["id"]),
                  Paragraph(f"{TYPE_LABEL[s['type']].upper()} · {s['id']}", S["kicker"]),
                  Paragraph("Original report", S["h1"]),
                  Paragraph(f"{len(s['source'].split())} words. Followed by {len(versions)} simplified version{'s' if len(versions) != 1 else ''}.", S["note"])]
        story += paragraphs(s["source"], S["source"], keep_lines=(s["type"] != "discharge"))

        for letter, r in zip(letters, versions):
            key_rows.append({
                "report": s["id"], "version": letter, "model_label": MODEL_NAMES.get(r["model"], r["model"]),
                "model_that_ran": actual_model(r), "strategy": r["strategy"],
                "entity_list_used": r.get("strategy") == "ner-guided" and r.get("ner_extraction_status") == "success",
                "trial_id": r["trial_id"],
            })
            story += [CondPageBreak(6 * cm), Spacer(1, 6),
                      Paragraph(f"Simplified version {letter}", S["h2"])]
            story += paragraphs(r["output_text"], S["body"])
            story += [Spacer(1, 4), KeepTogether([review_form(letter)]), Spacer(1, 10)]

    doc.build(story)

    with open(OUT_KEY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0].keys()))
        w.writeheader()
        w.writerows(key_rows)
    print(f"Wrote {OUT_PDF} ({len(included)} reports, {len(key_rows)} versions) and {OUT_KEY}")


if __name__ == "__main__":
    main()
