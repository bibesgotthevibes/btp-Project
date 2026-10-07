"""
analysis/prompts/builder.py
───────────────────────────
Unified prompt assembler dispatching across:
- Tasks: 'summarization' | 'simplification'
- Datatypes: 'discharge' | 'pathology' | 'radiology'
- Strategies: 'zero-shot' | 'few-shot' | 'ner-guided'

For 'ner-guided' strategy (simplification only):
  - Stage 1: build_ner_extraction_prompt(datatype, text)
             → messages for NER extraction call (returns structured JSON)
  - Stage 2: build_ner_guided_prompt(task, datatype, text, ner_retention_block)
             → messages for simplification call with injected entity constraints
"""

from typing import Dict, List, Tuple, Any

from .discharge_prompts import (
    DISCHARGE_SIMPLIFY_SYSTEM_PROMPT,
    DISCHARGE_SIMPLIFY_FEW_SHOT_EXAMPLES,
    DISCHARGE_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
    DISCHARGE_SUMMARIZE_SYSTEM_PROMPT,
    DISCHARGE_SUMMARIZE_FEW_SHOT_EXAMPLES,
)
from .pathology_prompts import (
    PATHOLOGY_SIMPLIFY_SYSTEM_PROMPT,
    PATHOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES,
    PATHOLOGY_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
    PATHOLOGY_SUMMARIZE_SYSTEM_PROMPT,
    PATHOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
)
from .radiology_prompts import (
    RADIOLOGY_SIMPLIFY_SYSTEM_PROMPT,
    RADIOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES,
    RADIOLOGY_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
    RADIOLOGY_SUMMARIZE_SYSTEM_PROMPT,
    RADIOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
    RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT,
    RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES,
)
from .ner_extraction_prompts import build_ner_extraction_messages
from .json_parser import ner_json_to_retention_block

# ── Standard Prompt Registry (zero-shot / few-shot) ───────────────────────────
PROMPT_REGISTRY = {
    ("discharge", "simplification"): {
        "system": DISCHARGE_SIMPLIFY_SYSTEM_PROMPT,
        "few_shot": DISCHARGE_SIMPLIFY_FEW_SHOT_EXAMPLES,
        "task_label": "simplify the following discharge summary into simple, plain Indian English for family members",
    },
    ("discharge", "summarization"): {
        "system": DISCHARGE_SUMMARIZE_SYSTEM_PROMPT,
        "few_shot": DISCHARGE_SUMMARIZE_FEW_SHOT_EXAMPLES,
        "task_label": "summarize the following discharge summary into a structured clinical summary for healthcare providers",
    },
    ("pathology", "simplification"): {
        "system": PATHOLOGY_SIMPLIFY_SYSTEM_PROMPT,
        "few_shot": PATHOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES,
        "task_label": "simplify the following surgical pathology report into plain English that a patient can understand",
    },
    ("pathology", "summarization"): {
        "system": PATHOLOGY_SUMMARIZE_SYSTEM_PROMPT,
        "few_shot": PATHOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
        "task_label": "summarize the following pathology report into a structured oncologic summary for physicians",
    },
    ("radiology", "simplification"): {
        "system": RADIOLOGY_SIMPLIFY_SYSTEM_PROMPT,
        "few_shot": RADIOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES,
        "task_label": "simplify the following radiology report into plain English for the patient and family",
    },
    # Chest X-ray variant for the Open-i reference benchmark (run_openi.py --prompt cxr)
    ("radiology_cxr", "simplification"): {
        "system": RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT,
        "few_shot": RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES,
        "task_label": "rewrite the following chest X-ray report in plain English for the patient",
    },
    ("radiology", "summarization"): {
        "system": RADIOLOGY_SUMMARIZE_SYSTEM_PROMPT,
        "few_shot": RADIOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
        "task_label": "summarize the following radiology report into a structured imaging summary for referring physicians",
    },
}

# ── NER-Guided System Prompts Registry ────────────────────────────────────────
NER_GUIDED_SYSTEM_PROMPTS = {
    ("discharge", "simplification"): DISCHARGE_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
    ("pathology", "simplification"): PATHOLOGY_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
    ("radiology", "simplification"): RADIOLOGY_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
}


def build_prompt(
    task: str,
    datatype: str,
    strategy: str,
    text: str,
) -> Tuple[str, str, List[Dict[str, str]]]:
    """
    Build structured prompt messages for zero-shot or few-shot strategies.

    For 'ner-guided' strategy, use build_ner_extraction_prompt() for Stage 1
    and build_ner_guided_prompt() for Stage 2 instead of this function.

    Returns:
        (system_prompt, user_content, messages_list)
    """
    dt = datatype.lower()
    tk = task.lower()
    st = strategy.lower()

    key = (dt, tk)
    if key not in PROMPT_REGISTRY:
        raise ValueError(
            f"Unknown (datatype, task) combination: {key}. "
            f"Supported: {list(PROMPT_REGISTRY.keys())}"
        )

    entry = PROMPT_REGISTRY[key]
    system_prompt = entry["system"]
    few_shot_examples = entry["few_shot"]
    task_label = entry["task_label"]

    user_parts = []

    if st == "few-shot" and few_shot_examples:
        user_parts.append("Here are examples of what I expect:\n")
        for i, eg in enumerate(few_shot_examples):
            user_parts.append(f"--- Example {i+1} ---")
            user_parts.append(f"Original Medical Report:\n{eg['input'].strip()}\n")
            user_parts.append(f"Output:\n{eg['output'].strip()}\n")

    user_parts.append("--- Your Task ---")
    user_parts.append(f"Please {task_label}:\n")
    user_parts.append(f"Original Medical Report:\n{text.strip()}\n")
    user_parts.append("Output:\n")

    user_content = "\n".join(user_parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    return system_prompt, user_content, messages


def build_ner_extraction_prompt(
    datatype: str,
    text: str,
) -> Tuple[str, str, List[Dict[str, str]]]:
    """
    Build Stage 1 NER extraction messages for the ner-guided strategy.

    Args:
        datatype: One of 'discharge', 'pathology', 'radiology'.
        text: The raw medical report text.

    Returns:
        (system_prompt, user_content, messages_list)
        system_prompt = the NER extraction system prompt
        user_content  = the one-shot example folded in, then the actual extraction request
        messages_list = the full one-shot messages array
    """
    messages = build_ner_extraction_messages(datatype, text)
    system_prompt = messages[0]["content"]
    # Providers take only (system, user), so fold the example user/assistant turns into
    # the user content; sending only messages[-1] silently dropped the one-shot example.
    example = [f"Example request:\n{m['content']}" if m["role"] == "user" else f"Example JSON answer:\n{m['content']}"
               for m in messages[1:-1]]
    user_content = "\n\n".join(example + [messages[-1]["content"]])
    return system_prompt, user_content, messages


def build_ner_guided_prompt(
    task: str,
    datatype: str,
    text: str,
    ner_json: dict,
) -> Tuple[str, str, List[Dict[str, str]]]:
    """
    Build Stage 2 NER-guided simplification messages.

    Injects the extracted NER JSON as a human-readable retention constraint
    block into the system prompt before the rules section.

    Args:
        task: Must be 'simplification' (ner-guided only applies to simplification).
        datatype: One of 'discharge', 'pathology', 'radiology'.
        text: The raw medical report text.
        ner_json: The parsed NER extraction dict from Stage 1.

    Returns:
        (system_prompt, user_content, messages_list)
    """
    dt = datatype.lower()
    tk = task.lower()
    key = (dt, tk)

    if key not in NER_GUIDED_SYSTEM_PROMPTS:
        raise ValueError(
            f"NER-guided strategy is only supported for simplification. "
            f"Got task='{task}', datatype='{datatype}'. "
            f"Supported: {list(NER_GUIDED_SYSTEM_PROMPTS.keys())}"
        )

    # Build the human-readable retention block from the NER JSON
    retention_block = ner_json_to_retention_block(ner_json, dt)

    # Inject the retention block into the system prompt template
    raw_system_template = NER_GUIDED_SYSTEM_PROMPTS[key]
    system_prompt = raw_system_template.replace("{ner_retention_block}", retention_block)

    # Task labels for simplification
    task_labels = {
        "discharge": "simplify the following discharge summary into simple, plain Indian English for family members",
        "pathology": "simplify the following surgical pathology report into plain English that a patient can understand",
        "radiology": "simplify the following radiology report into plain English for the patient and family",
    }
    task_label = task_labels.get(dt, f"simplify the following {dt} medical report")

    user_parts = [
        "--- Your Task ---",
        f"Please {task_label}:\n",
        f"Original Medical Report:\n{text.strip()}\n",
        "Output:\n",
    ]
    user_content = "\n".join(user_parts)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    return system_prompt, user_content, messages
