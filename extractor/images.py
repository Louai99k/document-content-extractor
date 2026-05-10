import base64
import os
import time


def describe_image(img_path, config):
    mode = config["image"]["mode"]
    if mode == "skip":
        return None
    if mode == "extract":
        return "Image saved"
    if mode == "ocr":
        return _ocr(img_path, config)
    if mode == "llm":
        desc = _llm(img_path, config)
        if desc:
            return desc
        ocr = _ocr(img_path, config)
        if ocr:
            return f"[LLM backends all failed] {ocr}"
        return "[LLM backends all failed, no OCR text found]"
    return None


def _llm(img_path, config):
    llm_cfg = config["image"].get("llm", {})
    backend = llm_cfg.get("backend", "auto")

    if backend == "auto":
        backend = _auto_select_backend()

    print(f"    LLM backend: {backend}")

    if backend == "gemini":
        return _gemini(img_path, llm_cfg)
    if backend == "ollama":
        return _ollama(img_path, llm_cfg)
    if backend == "huggingface":
        return _huggingface(img_path, llm_cfg)
    return None


def _auto_select_backend():
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OLLAMA_HOST"):
        return "ollama"
    return "huggingface"


_WORKING_GEMINI_MODEL = None


def _discover_gemini_models(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        import requests
        resp = requests.get(url, timeout=10)
        if resp.ok:
            models = resp.json().get("models", [])
            candidates = []
            for m in models:
                name = m.get("name", "")
                methods = m.get("supportedGenerationMethods", [])
                if name.startswith("models/gemini-") and "generateContent" in methods:
                    candidates.append(name.replace("models/", ""))
            # Prefer flash, then pro
            flash = [m for m in candidates if "flash" in m]
            pro = [m for m in candidates if "pro" in m and m not in flash]
            return flash + pro + candidates
    except Exception:
        pass
    return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash", "gemini-1.5-pro"]


def _gemini(img_path, cfg):
    global _WORKING_GEMINI_MODEL
    import requests
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("    GEMINI_API_KEY not set")
        return None

    if _WORKING_GEMINI_MODEL is None:
        configured = cfg.get("gemini", {}).get("model", "")
        discovered = _discover_gemini_models(api_key)
        if configured and configured in discovered:
            _WORKING_GEMINI_MODEL = configured
        else:
            _WORKING_GEMINI_MODEL = discovered[0] if discovered else "gemini-2.0-flash"
        print(f"    Gemini model: {_WORKING_GEMINI_MODEL}")

    model = _WORKING_GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(img_path)[1].lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")

    payload = {
        "contents": [{
            "parts": [
                {"text": "Describe this image in detail. Focus on technical diagrams, charts, code, or document content."},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]
        }]
    }
    resp = requests.post(url, json=payload, timeout=60)
    if resp.ok:
        candidates = resp.json().get("candidates", [])
        if candidates:
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            return f"Gemini: {text[:600]}" if text else None
    print(f"    Gemini error: {resp.status_code} {resp.text[:200]}")
    return None


def _ollama(img_path, cfg):
    import requests
    host = cfg.get("ollama", {}).get("host", os.environ.get("OLLAMA_HOST", "http://ollama:11434"))
    model = cfg.get("ollama", {}).get("model", "llava:7b")

    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": model,
        "prompt": "Describe this image in detail, focusing on technical content.",
        "images": [b64],
        "stream": False,
    }
    try:
        resp = requests.post(f"{host}/api/generate", json=payload, timeout=120)
        if resp.ok:
            text = resp.json().get("response", "").strip()
            return f"Ollama: {text[:600]}" if text else None
        print(f"    Ollama error: {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"    Ollama not reachable at {host}")
    return None


def _huggingface(img_path, cfg):
    import requests
    model = cfg.get("huggingface", {}).get("model", "Salesforce/blip-image-captioning-large")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Content-Type": "application/octet-stream"}
    api_key = os.environ.get("HF_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with open(img_path, "rb") as f:
        data = f.read()

    for attempt in range(5):
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=120)
            if resp.ok:
                result = resp.json()
                if isinstance(result, list) and result:
                    text = result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    text = result.get("generated_text", "").strip()
                else:
                    return None
                return f"HF: {text[:600]}" if text else None
            if resp.status_code == 503:
                print(f"    HF model loading (attempt {attempt+1}/5), waiting 15s...")
                time.sleep(15)
                continue
            print(f"    HF error: {resp.status_code} {resp.text[:200]}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"    HF network error (attempt {attempt+1}/5), retrying...")
            time.sleep(5)
            continue

    print("    HF: model failed to load after 5 attempts")
    return None


def _ocr(img_path, config):
    try:
        import pytesseract
        from PIL import Image
        lang = config["image"].get("ocr_lang", "eng")
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img, lang=lang).strip()
        return f"OCR: {text[:500]}" if text else None
    except Exception:
        return None
