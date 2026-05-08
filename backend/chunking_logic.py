import torch

def generate_scifive_chunked(text, model, tokenizer, device):
    CHUNK_TOKENS  = 450
    CHUNK_OVERLAP = 50
    TASK_PREFIX = "lay simplify preserving all details: "
    
    if not isinstance(text, str) or len(text.strip()) == 0:
        return text if isinstance(text, str) else ""

    full_ids = tokenizer(text, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    prefix_ids = tokenizer(TASK_PREFIX, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    eos_id  = tokenizer.eos_token_id
    total   = full_ids.shape[0]

    chunk_outputs = []
    start = 0
    while start < total:
        end = min(start + CHUNK_TOKENS, total)
        chunk_body = full_ids[start:end]
        
        # [prefix] + [chunk body] + [EOS]
        chunk_with_prefix = torch.cat([
            prefix_ids,
            chunk_body,
            torch.tensor([eos_id])
        ])
        
        inp = chunk_with_prefix.unsqueeze(0).to(device)
        attn = torch.ones_like(inp)
        n_tokens = inp.shape[-1]
        chunk_body_len = chunk_body.shape[0]
        
        # Prevent forcing long sequences on very short trailing chunks (avoids babbling)
        dyn_min = max(5, int(n_tokens * 0.55)) if chunk_body_len > 25 else 0

        with torch.no_grad():
            out_ids = model.generate(
                input_ids=inp,
                attention_mask=attn,
                max_new_tokens=min(n_tokens, 512),
                min_length=dyn_min,
                num_beams=4,
                length_penalty=1.5,
                early_stopping=True,
                no_repeat_ngram_size=4,
            )
            
        passage = tokenizer.decode(out_ids[0], skip_special_tokens=True).strip()
        if passage:
            chunk_outputs.append(passage)
            
        if end >= total:
            break
        start = end - CHUNK_OVERLAP
        
    return " ".join(chunk_outputs)


def generate_biobart_chunked(text, model, tokenizer, device):
    CHUNK_TOKENS  = 450
    CHUNK_OVERLAP = 50
    
    if not isinstance(text, str) or len(text.strip()) == 0:
        return text if isinstance(text, str) else ""

    full_ids = tokenizer(text, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    eos_id  = tokenizer.eos_token_id
    total   = full_ids.shape[0]

    chunk_outputs = []
    start = 0
    while start < total:
        end = min(start + CHUNK_TOKENS, total)
        chunk_body = full_ids[start:end]
        
        # [chunk body] + [EOS]
        chunk_with_eos = torch.cat([
            chunk_body,
            torch.tensor([eos_id])
        ])
        
        inp = chunk_with_eos.unsqueeze(0).to(device)
        attn = torch.ones_like(inp)
        n_tokens = inp.shape[-1]
        chunk_body_len = chunk_body.shape[0]
        
        # Prevent forcing long sequences on very short trailing chunks
        dyn_min = max(5, int(n_tokens * 0.55)) if chunk_body_len > 25 else 0

        with torch.no_grad():
            out_ids = model.generate(
                input_ids=inp,
                attention_mask=attn,
                max_new_tokens=min(n_tokens, 512),
                min_length=dyn_min,
                num_beams=4,
                length_penalty=1.5,
                early_stopping=True,
                no_repeat_ngram_size=4,
            )
            
        passage = tokenizer.decode(out_ids[0], skip_special_tokens=True).strip()
        if passage:
            chunk_outputs.append(passage)
            
        if end >= total:
            break
        start = end - CHUNK_OVERLAP
        
    return " ".join(chunk_outputs)


def generate_biogpt_chunked(text, model, tokenizer, device):
    CHUNK_TOKENS  = 400
    CHUNK_OVERLAP = 50
    PROMPT_PREFIX = "lay simplify preserving all details: "
    PROMPT_SUFFIX = "\n### Simplified: "

    if not isinstance(text, str) or len(text.strip()) == 0:
        return text if isinstance(text, str) else ""

    full_ids = tokenizer(text, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    prefix_ids = tokenizer(PROMPT_PREFIX, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    suffix_ids = tokenizer(PROMPT_SUFFIX, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
    total = full_ids.shape[0]

    chunk_outputs = []
    start = 0
    while start < total:
        end = min(start + CHUNK_TOKENS, total)
        chunk_body = full_ids[start:end]
        
        # [prefix] + [chunk body] + [suffix]
        chunk_with_prompt = torch.cat([prefix_ids, chunk_body, suffix_ids])

        inp = chunk_with_prompt.unsqueeze(0).to(device)
        attn = torch.ones_like(inp)
        prompt_len = inp.shape[-1]
        chunk_body_len = chunk_body.shape[0]
        
        # dyn_min_new logic for causal LM: skip for short trailing chunks
        dyn_min_new = max(5, int((prompt_len - 15) * 0.55)) if chunk_body_len > 25 else 0

        with torch.no_grad():
            out_ids = model.generate(
                input_ids=inp,
                attention_mask=attn,
                max_new_tokens=min(prompt_len, 512),
                min_new_tokens=dyn_min_new,
                num_beams=4,
                length_penalty=1.5,
                early_stopping=True,
                no_repeat_ngram_size=4,
            )
            
        # Extract new tokens (causal LM output)
        new_tokens = out_ids[0, inp.shape[1]:]  
        passage = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        if passage:
            chunk_outputs.append(passage)
            
        if end >= total:
            break
        start = end - CHUNK_OVERLAP

    return " ".join(chunk_outputs)
