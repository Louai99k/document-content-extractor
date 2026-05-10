import argparse
import glob
import os
import sys
import yaml
from datetime import datetime

from .parsers.pdf import parse_pdf
from .parsers.docx import parse_docx


def load_config():
    path = os.environ.get("CONFIG_PATH", "/app/config.yaml")
    defaults = {
        "input_dir": "/data/input",
        "output_dir": "/data/output",
        "output_mode": "both",
        "image": {
            "mode": "ocr",
            "ocr_lang": "tur+eng",
            "llm": {
                "backend": "auto",
                "gemini": {"model": "gemini-1.5-flash"},
                "ollama": {"model": "llava:7b", "host": "http://ollama:11434"},
                "huggingface": {"model": "Salesforce/blip-image-captioning-large"},
            },
        },
    }
    if os.path.exists(path):
        with open(path) as f:
            user = yaml.safe_load(f) or {}
        deep_merge(defaults, user)
    return defaults


def deep_merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and k in base and isinstance(base[k], dict):
            deep_merge(base[k], v)
        else:
            base[k] = v


def parse_args():
    p = argparse.ArgumentParser(description="Document Content Extractor")
    p.add_argument("--input", help="Input directory")
    p.add_argument("--output", help="Output directory")
    p.add_argument("--mode", choices=["combined", "per-file", "both"], help="Output mode")
    p.add_argument("--images", choices=["extract", "ocr", "llm", "skip"], help="Image handling")
    p.add_argument("--llm-backend", choices=["auto", "gemini", "ollama", "huggingface"], help="LLM backend for image description")
    p.add_argument("--ocr-lang", help="Tesseract OCR language(s)")
    return p.parse_args()


def main():
    config = load_config()
    args = parse_args()

    if args.input:
        config["input_dir"] = args.input
    if args.output:
        config["output_dir"] = args.output
    if args.mode:
        config["output_mode"] = args.mode
    if args.images:
        config["image"]["mode"] = args.images
    if args.llm_backend:
        config["image"]["llm"]["backend"] = args.llm_backend
    if args.ocr_lang:
        config["image"]["ocr_lang"] = args.ocr_lang

    in_dir = config["input_dir"]
    out_dir = config["output_dir"]
    mode = config["output_mode"]

    os.makedirs(out_dir, exist_ok=True)
    if mode in ("per-file", "both"):
        os.makedirs(os.path.join(out_dir, "per-file"), exist_ok=True)
    if config["image"]["mode"] != "skip":
        os.makedirs(os.path.join(out_dir, "images"), exist_ok=True)

    pdfs = sorted(glob.glob(os.path.join(in_dir, "**", "*.pdf"), recursive=True))
    docxs = sorted(glob.glob(os.path.join(in_dir, "**", "*.docx"), recursive=True))

    if not pdfs and not docxs:
        print(f"No PDF or DOCX files found in {in_dir}")
        sys.exit(0)

    combined = []
    header = (
        "CONTENT DUMP\n"
        f"{'='*40}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Source: {in_dir}\n"
        f"Files: {len(pdfs)} PDF, {len(docxs)} DOCX\n"
        f"{'='*40}\n"
    )
    combined.append(header)

    for fp in pdfs:
        print(f"  PDF: {os.path.basename(fp)}")
        try:
            text = parse_pdf(fp, out_dir, config)
            combined.append(text)
            write_per_file(out_dir, fp, text, mode)
            print(f"    OK")
        except Exception as e:
            print(f"    ERR: {e}")
            combined.append(f"\n[ERROR: {os.path.basename(fp)} - {e}]\n")

    for fp in docxs:
        print(f"  DOCX: {os.path.basename(fp)}")
        try:
            text = parse_docx(fp, out_dir, config)
            combined.append(text)
            write_per_file(out_dir, fp, text, mode)
            print(f"    OK")
        except Exception as e:
            print(f"    ERR: {e}")
            combined.append(f"\n[ERROR: {os.path.basename(fp)} - {e}]\n")

    if mode in ("combined", "both"):
        body = "\n\n".join(combined)
        path = os.path.join(out_dir, "Context_Dump.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"\nCombined: {path} ({len(body):,} chars)")

    print("Done.")


def write_per_file(out_dir, src_path, text, mode):
    if mode not in ("per-file", "both"):
        return
    name = os.path.basename(src_path) + ".txt"
    path = os.path.join(out_dir, "per-file", name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
