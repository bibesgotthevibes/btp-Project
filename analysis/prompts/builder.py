"""
analysis/prompts/builder.py
───────────────────────────
Unified prompt assembler dispatching across:
- Tasks: 'summarization' | 'simplification'
- Datatypes: 'discharge' | 'pathology' | 'radiology'
- Strategies: 'zero-shot' | 'few-shot'
"""

from typing import Dict, List, Tuple, Any

from .discharge_prompts import (
    DISCHARGE_SIMPLIFY_SYSTEM_PROMPT,
    DISCHARGE_SIMPLIFY_FEW_SHOT_EXAMPLES,
    DISCHARGE_SUMMARIZE_SYSTEM_PROMPT,
    DISCHARGE_SUMMARIZE_FEW_SHOT_EXAMPLES,
)
from .pathology_prompts import (
    PATHOLOGY_SIMPLIFY_SYSTEM_PROMPT,
    PATHOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES,
    PATHOLOGY_SUMMARIZE_SYSTEM_PROMPT,
    PATHOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
)
from .radiology_prompts import (
    RADIOLOGY_SIMPLIFY_SYSTEM_PROMPT,
    RADIOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES,
    RADIOLOGY_SUMMARIZE_SYSTEM_PROMPT,
    RADIOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
)

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
    ("radiology", "summarization"): {
        "system": RADIOLOGY_SUMMARIZE_SYSTEM_PROMPT,
        "few_shot": RADIOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES,
        "task_label": "summarize the following radiology report into a structured imaging summary for referring physicians",
    },
}

def build_prompt(
    task: str,
    datatype: str,
    strategy: str,
    text: str,
) -> Tuple[str, str, List[Dict[str, str]]]:
    """
    Build structured prompt messages for the specified configuration.
    
    Returns:
        (system_prompt, user_content, messages_list)
        where messages_list has standard OpenAI/Gemini chat format:
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    """
    dt = datatype.lower()
    tk = task.lower()
    st = strategy.lower()

    key = (dt, tk)
    if key not in PROMPT_REGISTRY:
        raise ValueError(f"Unknown (datatype, task) combination: {key}. Supported: {list(PROMPT_REGISTRY.keys())}")

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
