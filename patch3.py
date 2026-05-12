import re
with open("backend/app.py", "r") as f:
    orig = f.read()

if "import requests" not in orig:
    orig = orig.replace("import os\n", "import os\nimport requests\n")

new_code = """
def _text_chunk_hf(text, max_words=150, overlap=30):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks

def _call_hf_inference(text, hf_repo, prefix="", suffix=""):
    API_URL = f"https://api-inference.huggingface.co/models/{hf_repo}"
    
    # HF is public, token is optional but helps with rate limits
    hf_token = os.getenv("HF_TOKEN", "")
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    
    chunks = _text_chunk_hf(text)
    outputs = []
    
    import requests
    for chunk in chunks:
        payload = {
            "inputs": prefix + chunk + suffix,
            "inputs": pr:                       "inputs": pr:                          "input":             "inputs": pr:    nalty": 1.5,
                "early_stopping": True,
                "no_repe             ":                "no_repe             ":            os                "no_reper              d)         
                                0:                              er                                0:           s.tex                                              .j                         ce(js              and "generated_text" in json_res[0]:
            out_text = json_res[0]["generated_text"]
            out_text = out_text.replace(prefix    hunk + suffix, "").strip()
            outputs.append(out_text)
        elif "error" in json_res:
            return jsonify({"error": f"HF API Model Error: {json_res['error']}"}), 502
                                  ut    )

def _call_deffidef _call_deffegy="zdef _call_deffidef _cmethdef _call_deffide redef _call_deffidef _call_deffegy="zdef _calive"def _call_deffidef _call_deffegy="zdef _call_deffidef _cmethdef _call_deffide redef _call_deffidef _call_deffegy="zdef _calive"def _call mdef _call_deffidef _call_deffegy="zdefreturn jsonify({"result": res, "model": model_info["name"] if model_info else "SciFive", "tokens": None})

def _call_biobart(text, strategy="zero-shot", selection_method="random"):
    res = _call_hf_inference(text, "11Raghav/BioBART")
    if isinstance(res, tuple): return res 
    model_info = next((m for m in MODELS if m["id"] == "biobart-local"), None)
    return jsonify({"result": res, "model": model_info["name"] if model_info else "BioBART", "tokens": None})

def _call_biogpt(text, strategy="zero-shot", selectdef _call_biogpt(text, strategy="calldef _call_biogpt(text, strategy=oGdef _call_biogpt(text, strategy="zero-shot", selectdef _call_biogpt(text, strategy="   def _call_biogpt(text, strategy="zero-
    model_info = next((m for m in MODELS if m["id"] == "biogpt-local"), None)
    return jsonify({"result": res, "model": model_info["name"] if model_info else "BioGPT", "tokens": None})

def _call_cerebras("""

orig = re.sub(r"def _call_scifive\(.*?def _call_cerebras\(", new_code, orig, flags=re.DOTALL)

with open("backend/app.py", "w") as f:
    f.write(orig)

