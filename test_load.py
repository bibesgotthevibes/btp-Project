import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

hf_token = os.getenv("HF_TOKEN", "")
token_kwarg = {"token": hf_token} if hf_token else {}
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained("11Raghav/SciFive", extra_special_tokens={}, **token_kwarg)
print("Tokenizer loaded.")
model = AutoModelForSeq2SeqLM.from_pretrained("11Raghav/SciFive", **token_kwarg)
print("Model loaded.")
