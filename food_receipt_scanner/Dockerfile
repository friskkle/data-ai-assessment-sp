FROM python:3.10-slim

# Tesseract for OCR, libgl/libglib for OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY food_receipt_scanner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY food_receipt_scanner/ ./food_receipt_scanner/

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "-m", "food_receipt_scanner.app"]
