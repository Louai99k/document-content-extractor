# Document Content Extractor

Extract text + images from PDF and DOCX files. Single combined dump and/or per-file output. Image description via OCR (built-in) or cloud/local LLM.

## Quick Start

1. Drop PDFs/DOCX into `input/`
2. Run:

```bash
./run.sh
```

3. Get output in `output/`:
   - `Context_Dump.txt` — all files concatenated
   - `per-file/` — one `.txt` per source
   - `images/` — extracted images

## Usage

```bash
# Default: combined dump + per-file + OCR on images
./run.sh

# Per-file only, no image processing
./run.sh --mode per-file --images skip

# Override input/output dirs
./run.sh --input /path/to/docs --output /path/to/out

# Set OCR language (default: tur+eng)
./run.sh --ocr-lang eng
```

## Output Modes (`--mode`)

| Mode | Output |
|------|--------|
| `combined` | Single `Context_Dump.txt` |
| `per-file` | Per-source `.txt` in `output/per-file/` |
| `both` (default) | Both |

## Image Handling (`--images`)

| Mode | Behavior |
|------|----------|
| `ocr` (default) | Extract images + run tesseract OCR |
| `llm` | Describe images via LLM (cloud or local, see below) |
| `extract` | Save images only, no description |
| `skip` | Ignore images entirely |

### LLM Backends (`--llm-backend`)

When `--images llm`, the backend is chosen automatically:

| Backend | How it works | Setup |
|---------|-------------|-------|
| `gemini` (default if key found) | Google Gemini 1.5 Flash API | Set `GEMINI_API_KEY` env var. Free from [aistudio.google.com](https://aistudio.google.com/apikey) — no credit card needed |
| `ollama` | Local Ollama with vision model | Requires Ollama running + image model pulled |
| `huggingface` | HuggingFace Inference API | No setup needed (rate-limited free tier). Optional `HF_API_KEY` for higher limits |
| `auto` (default) | Checks `GEMINI_API_KEY` → `OLLAMA_HOST` → HuggingFace free | — |

**Gemini (recommended cloud — free, no credit card):**

1. Get API key: https://aistudio.google.com/apikey
2. Copy `.env.example` to `.env` and set key:

```bash
cp .env.example .env
# Edit .env → GEMINI_API_KEY=your_key_here
```
3. Run:

```bash
./run.sh --images llm
```

**Local Ollama:**
```bash
docker compose -f docker-compose.yml -f docker-compose.vision.yml run --rm extractor --images llm
```

This starts Ollama with `llava:7b`, downloads model on first run (~4GB).

**Force specific backend:**
```bash
./run.sh --images llm --llm-backend gemini
./run.sh --images llm --llm-backend huggingface
```

## Config

`config.yaml` sets defaults. CLI flags override.

```yaml
input_dir: /data/input
output_dir: /data/output
output_mode: both

image:
  mode: ocr
  ocr_lang: tur+eng
  llm:
    backend: auto
    gemini:
      model: gemini-1.5-flash
    ollama:
      model: llava:7b
      host: http://ollama:11434
    huggingface:
      model: Salesforce/blip-image-captioning-large
```

Override config path:
```bash
docker compose run --rm -e CONFIG_PATH=/data/custom.yaml extractor
```

## Setup

1. `cp .env.example .env`  
2. Fill in API keys in `.env`  
3. `.env` is gitignored — keys stay local

## Environment Variables

| Variable | How to set | Purpose |
|----------|-----------|---------|
| `GEMINI_API_KEY` | `.env` file | Google Gemini API key (free, no credit card) |
| `HF_API_KEY` | `.env` file | HuggingFace API key (optional, higher rate limits) |
| `OLLAMA_HOST` | `.env` or compose | Ollama server URL |
| `CONFIG_PATH` | `.env` or CLI | Path to custom config YAML |

## Direct Python (no Docker)

```bash
pip install PyMuPDF python-docx Pillow pytesseract pyyaml requests
python -m extractor --input ./my_docs --output ./out
```

## Structure

```
├── config.yaml
├── Dockerfile
├── docker-compose.yml
├── docker-compose.vision.yml
├── run.sh
├── input/              # Place source files here
├── output/             # Results
│   ├── Context_Dump.txt
│   ├── per-file/
│   └── images/
└── extractor/
    ├── cli.py          # Entry, CLI parsing
    ├── images.py       # Image description: Gemini/Ollama/HF/OCR
    └── parsers/
        ├── pdf.py      # PDF text + image extraction
        └── docx.py     # DOCX text + tables + images
```
