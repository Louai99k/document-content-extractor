FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    PyMuPDF==1.24.5 \
    python-docx==1.1.2 \
    Pillow==10.4.0 \
    pytesseract==0.3.10 \
    pyyaml==6.0.2 \
    requests==2.32.3

COPY config.yaml .
COPY extractor/ extractor/

VOLUME ["/data/input", "/data/output"]

ENTRYPOINT ["python", "-m", "extractor"]
CMD ["--mode", "both", "--images", "ocr"]
