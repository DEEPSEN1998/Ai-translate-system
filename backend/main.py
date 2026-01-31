# ===========================
# IMPORTS
# ===========================
import json
import os
import hashlib
import time
import threading
import gc

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from fastapi.middleware.cors import CORSMiddleware

# ===========================
# THREAD LOCKS
# ===========================
model_lock = threading.Lock()
cache_lock = threading.Lock()

# ===========================
# DATA DIRECTORY (PER SITE CACHE)
# ===========================
DATA_DIR = "data"

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def site_cache_file(site_id: str):
    ensure_data_dir()
    safe = site_id.replace("/", "_")
    return os.path.join(DATA_DIR, f"{safe}.json")

def load_site_cache(site_id):
    path = site_cache_file(site_id)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_site_cache(site_id, cache):
    path = site_cache_file(site_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# ===========================
# HASH
# ===========================
def make_hash(text):
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

# ===========================
# DEVICE
# ===========================
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

# ===========================
# MODEL
# ===========================
MODEL_PATH = "models/nllb-200-distilled-600M"

tokenizer = None
model = None

def load_model():
    global tokenizer, model
    with model_lock:
        if model is None:
            print("Loading NLLB model...")
            tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
            model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
            model = model.to(device)

def unload_model():
    global tokenizer, model
    with model_lock:
        if model is not None:
            del model
            del tokenizer
            model = None
            tokenizer = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

# ===========================
# FASTAPI APP
# ===========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ===========================
# REQUEST SCHEMA
# ===========================
class TranslateRequest(BaseModel):
    texts: list[str]
    target_lang: str   # bn | hi | en
    site_id: str

# ===========================
# LANGUAGE MAP
# ===========================
LANG_MAP = {
    "bn": "ben_Beng",
    "hi": "hin_Deva"
}

# ===========================
# TRANSLATE ENDPOINT
# ===========================
@app.post("/translate")
def translate(req: TranslateRequest):

    start = time.perf_counter()

    # English needs no translation
    if req.target_lang == "en":
        return {"translations": req.texts}

    site_id = req.site_id
    target_lang = req.target_lang

    with cache_lock:
        cache = load_site_cache(site_id)

    results = [None] * len(req.texts)
    missing_items = []
    cache_modified = False

    # ---------------------------
    # CHECK CACHE FIRST
    # ---------------------------
    for i, text in enumerate(req.texts):
        clean = text.strip()
        key = make_hash(clean)

        entry = cache.get(key)

        if entry and target_lang in entry:
            results[i] = entry[target_lang]
        else:
            if not entry:
                cache[key] = {"en": clean}
                cache_modified = True
            missing_items.append((i, clean, key))

    # ---------------------------
    # RUN MODEL ONLY IF NEEDED
    # ---------------------------
    model_used = False

    if missing_items:
        model_used = True
        load_model()

        for idx, clean, key in missing_items:

            entry = cache[key]

            # Generate BOTH bn + hi once
            for lang in ["bn", "hi"]:
                if lang not in entry:
                    tokenizer.src_lang = "eng_Latn"
                    inputs = tokenizer(clean, return_tensors="pt").to(device)

                    with torch.inference_mode():
                        output = model.generate(
                            **inputs,
                            forced_bos_token_id=tokenizer.convert_tokens_to_ids(LANG_MAP[lang]),
                            max_length=256,
                            num_beams=4,
                            do_sample=False
                        )

                    entry[lang] = tokenizer.batch_decode(
                        output, skip_special_tokens=True
                    )[0]

                    cache_modified = True

            results[idx] = entry[target_lang]

        unload_model()

    # ---------------------------
    # SAVE CACHE
    # ---------------------------
    if cache_modified:
        with cache_lock:
            save_site_cache(site_id, cache)

    elapsed = round((time.perf_counter() - start) * 1000, 2)

    print(f"[{site_id}] {elapsed} ms | model_used={model_used}")

    return {
        "translations": results,
        "time_ms": elapsed,
        "model_used": model_used
    }

# ===========================
# HEALTH CHECK
# ===========================
@app.get("/")
def root():
    return {"status": "Translator API Running"}
