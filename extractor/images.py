import base64
import os


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
        return _ocr(img_path, config)
    return None


def _llm(img_path, config):
    llm_cfg = config["image"].get("llm", {})
    backend = llm_cfg.get("backend", "auto")

    if backend == "auto":
        backend = _auto_select_backend()

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


def _gemini(img_path, cfg):
    try:
        import requests
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        model = cfg.get("gemini", {}).get("model", "gemini-1.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"

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
        return None
    except Exception:
        return None


def _ollama(img_path, cfg):
    try:
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
        resp = requests.post(f"{host}/api/generate", json=payload, timeout=120)
        if resp.ok:
            text = resp.json().get("response", "").strip()
            return f"Ollama: {text[:600]}" if text else None
        return None
    except Exception:
        return None


def _huggingface(img_path, cfg):
    try:
        import requests
        model = cfg.get("huggingface", {}).get("model", "Salesforce/blip-image-captioning-large")
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Content-Type": "application/octet-stream"}
        api_key = os.environ.get("HF_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        with open(img_path, "rb") as f:
            data = f.read()

        resp = requests.post(url, headers=headers, data=data, timeout=60)
        if resp.ok:
            result = resp.json()
            if isinstance(result, list) and result:
                text = result[0].get("generated_text", "").strip()
            elif isinstance(result, dict):
                text = result.get("generated_text", "").strip()
            else:
                return None
            return f"HF: {text[:600]}" if text else None
        return None
    except Exception:
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
