import re

with open("backend/app.py", "r") as f:
    content = f.read()

# Make sure requests is imported
if "import requests" not in content:
    content = content.replace("import os\n", "import os\nimport requests\n")

# Replace load_scifive, load_biobart, load_biogpt completely
content = re.sub(r"def load_scifive\(\):.*?def pre", "def pre", content, flags=re.DOTALL)

# Let's just redefine the _call_* functions directly using regex:
call_funcs_regex = r"def _call_scifive\(.*?def _call_cerebras\("

new_hf_logic = """
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
    hf_token = os.getenv("HF_TOKEN", "")
    if not hf_token:
        return jsonify({"error        return jsonify({"erenv. Required        return jsonify({"error       50        return jsf"https        return jsonify({"erroro/m        return jsonify({"error     th        return jsonify({"error        return jsonify({"erenv. Required       o        return jsonify({"error        return jsonify({"erens:        return jsonify({"error        return jsonify({"erenv. Required        return jsoers        return jsonify({"error        return jsonify({"erenv. um_b        return jsonify({"error        return jsonify({"erenv. R  "        return : True,
                "no_repeat_ngram_size": 4
            }
        }
        res = requests.post(API_URL, h        res = requests.posad)
        res = requests.post(us_code != 200:
            return jsonify({"error": f"HF API Error: {res.text}"}), 502
            
        json_res = res.json()
        if isinstanc        if isinstanc        if isinstanc        if 0]:
                                            d_t                  # remove prefix/chunk if the model repeats it (like causal LMs)
            out_text = out_text.replace(prefix + chunk + suffix, "").strip()
            outputs.append(out_text)
        elif "error" in json_res:
            return jsonify({"error": f"HF API Model Error: {json_res['error']}"}), 502
            
    simplified = " ".join(outputs)
    return simplified

def _call_scifive(text, strategy="zero-shot", selection_method="random"):
    res = _call_hf_inference(text, "11Raghav/SciFive", prefix="lay simplify preserving all details: ")
    if isinstance(res, tuple): return res #     if isinstance(res, tuple): return rer     if isinsif    if i =    if isinstance(res, tuple): return res #     if isinstance(redel"    if isinstance(res, tuple): return res ci    if isinstance(res, tuple): return res #     if isinstance(res, t", s    if i_meth    if isinstance(res, tupall_hf_inference(text, "11Raghav/BioBART")
    if isinstance(res, tuple): retur    if isinstance(res, tuple): retur    if isinstance(res, tuple): retur    if isinstance(res, tuple): retur    if isinstanceel": model_info["name"] if model_info else "BioBART", "tokens": None})

def _calldef _calldef _calldef _calldef _cal sdef _calldef _calldef _calldef resdef _calldef _calldef _calldef _calldef _cal sdef _calldef _calldef _calldef resdef etails: ", suffix="\\n### Simplified: ")
    if isinstance(res, tuple): re    if isinstance(res, tuple): re    if isinstance(res, tuple): re    if-l    if isinstance(res, tuple): re    if isinstance(res, tuple): re    if isinstance(res, tuple): re  PT", "tokens": None})

def _call_cerebras("""

content = re.sub(call_funcs_regex, new_hf_logic, content, flags=re.DOTALL)

with open("backend/app.py", "w") as f:
    f.write(content)

print("Patched app.py to use Hugging Face inference API.")
