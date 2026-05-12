import re

with open("backend/app.py", "r") as f:
    orig = f.read()

# Make sure requests is imported
if "import requests" not in orig:
    orig = orig.replace("import os\n", "import os\nimport requests\n")

# Cleanly rebuild the functions
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
                                   put                                   pu                                    "max_new_tokens": 51                                4,                                   put                               ng"                           _repe             ": 4
            }
        }
        res = requests.post(API_URL, headers=header        resload)        res           res = requests.post00:        res = requests.post(A"er        res = requests.post(API_URL, headers=hetex        res = requests.post           res  res.j        res = requests.post(js        res = and "        res = requests.post(API_URL, headers=header        _res[0]["generated_text"]
            out_text = out_text.replace(prefix    hu            out_text = out_text.replace(prefix    hu                  elif "error" in json_res:
            return jsonify({"error": f"HF API Model Error: {json_res['error']}"}), 502
            
    return " ".join(outputs)

def _call_scifidef _call_scifide="zdef _call_scifidef _calthod="random"):
    res = _call_hf_inference(text, "11Raghav/SciFive", prefix="lay simplify preserving all details: ")
    if isinstance(res, tuple): return res 
    model_info = next((m for m in MODELS if m["id"] == "scifive-local"), None)
    return jsonify({"result": res, "model": mode    return j"]    rodel_info else "SciFive", "tokens": None})

def _call_biobart(text, strategy="zero-shot", selection_method="random"):
    res = _call_hf_inference(text, "11Raghav/BioBART")
    if isinstance(res, tuple): return res 
    model_info = next((m for m in MODELS if m["id"] == "biobart-local"), None)
    return jsonify({"result": res, "model": model_info["name"] if model_info else "Bi    return jsonify({"result": res, "model": model_info["name"] if model_info else "Bi    return jsonify({"result": res, "model": model_info["name"oG    return jsonify({"result": res, "model": model_info["name"] if model_info else "Bi      returance    return jsonify({"resu
                                                                          ne)
                                                                          ne)
lse "Bi    return jsoni None})

def _call_cerebras("""

# Regex repl# Regex repl# Regex repl# Regex repl# Regex repl# Regex repl# Regex repl# Regef# Regex repl# Regex repl# Regex repl# Regex repl# Regex repl# Regex repl# Regex repl# Regef# Regex repl#"w") as f:
    f.write(orig)

print("Patch 2 applied.")
