# AI Solution Engineer — Assessment Test

This repository is my submission for the technical test for Shopee. It is split into folders for each big task

---

## Repository structure

```
.
data/
  customers-100000.csv        # small dataset (not pushed to github)
  customers-2000000.csv       # large dataset (2M rows, not pushed to github)
  parse.ipynb                 # exploration and insights for taks 1-3
vector_db/  # Coding Test #4
  cosine_similarity.py        # cosine similarity written by hand (no np.dot / np.linalg.norm)
  embedding.py                # text -> vector (character-bigram count + hashing fallback)
  vector_db.py                # HashDB: in-memory index with disk persistence
  ingest.py                   # stream CSV -> build index -> save
  search.py                   # free-text query CLI
food_receipt_scanner/ # Coding Test #5
  app.py                      # Flask app (UI + upload + chat endpoints)
  ocr.py                      # Receipt parsing with opencv and pytesseract
  db.py                       # SQLite schema + the query "tools"
  agent.py                    # DeepSeek tool-calling loop
  config.py                   # env config (+ minimal .env loader)
  templates/index.html        # upload + chat UI
  requirements.txt
  Dockerfile
github/workflows/ci.yml        # CI/CD (builds & pushes the container)
```

---

## Part 1 — Data exploration

All findings are in `data/parse.ipynb`. Highlights:

- **100k dataset** is structurally clean: no nulls, 0 duplicate customer IDs and phone numbers, but 5 duplicated emails, ~49k repeated websites, and ~7k reused full names.
- **Phone numbers are messy**: 21 distinct formats, 10–18 digits, no consistent country code.
- **No seasonality** in subscription trends (an apparent February dip disappears when aggregating by month across years).
- **2M dataset**: I used **Polars lazy/streaming** to process it with a ~0.1 MB peak memory footprint, versus ~980 MB with a plain `pandas.read_csv`. The difference is that streaming processes the file row-by-row at query time instead of materializing the whole frame, and lazy evaluation lets the engine push down predicates/type casts.

---

## Part 4 — Vector database (cosine similarity from scratch)

A minimal vector database over the customer data: it embeds each customer's text fields into a fixed-size vector and answers similarity queries using a **hand-written cosine similarity** with plain Python mathematical formula.

### Functions

1. **Embedding** (`embedding.py`): text is lowercased, collapsed to single spaces, then turned into a **character-bigram count vector**. There is one dimension per possible letter pair over a 37-character alphabet, so the vector is a fixed 1369 dimensions regardless of vocabulary size. Bigrams keep word order, which is what lets `"jared jarvis"` match `"Jared Jarvis"`.
2. **Cosine similarity** (`cosine_similarity.py`): computed explicitly in one pass — dot product over the product of the L2 norms. Returns `0.0` for zero vectors.
3. **Index** (`vector_db.py`, `HashDB`): stores vectors + payloads, scores every vector against the query, returns top-k. `save`/`load` persist to `vectors.bin` (raw float64 via the stdlib `array` module) + `payloads.jsonl` + `meta.json`.

### Run

```bash
# build an index from the CSV
python -m vector_db.ingest --csv data/customers-100000.csv --index-dir data/index --limit 2000

# search by text
python -m vector_db.search "Joko Widodo" --index-dir data/index --top-k 5
python -m vector_db.search "Jackson Lee" --index-dir data/index --top-k 5
```

### Scaling note

A 1369-dim dense vector is fine for the demo, but at 2M rows it is memory-heavy. To scale up, can use hashing techniques and keep vector dimensions lower.

---

## Part 5 — Food receipt platform

A web app that (a) receives an uploaded receipt image, (b) extracts it with computer vision, (c) stores the parsed data, and (d) lets an LLM answer questions like *"What food did I buy yesterday?"* by calling database tools.

### Architecture

```
upload image ──> ocr.py (OpenCV + Tesseract) ──> parse_receipt() ──> db.py (SQLite)
user question ──> agent.py ──(tool call)──> db tools ──> LLM answer
```

- **Computer vision** (`ocr.py`): upscales the image, converts to grayscale, denoises, applies Otsu thresholding, then runs Tesseract (`--psm 6`). The raw text is parsed into `store`, `date`, `total`, and `items` with regex (trailing price per line, `TOTAL` keyword, date formats).
- **Storage** (`db.py`): SQLite with `receipts` and `items` tables.
- **Agent** (`agent.py`): a small tool-calling loop. The system prompt lists the available tools and today's date; the model replies with a JSON tool call, the tool runs against the real DB, the result is fed back, and the model gives a natural-language answer. Tools: `items_on_date`, `total_spend_on_date`, `find_item_in_range`.

### Setup

```
pip install -r food_receipt_scanner/requirements.txt
```

Requires Tesseract installed locally (`tesseract --version`).

Create `food_receipt_scanner/.env`:

```
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat   # or deepseek-reasoner
```

### Run

```bash
python -m food_receipt_scanner.app
# open http://localhost:5000
```

- Upload a receipt image and store in the DB.
- Ask questions in the chat box, e.g.:
  - "What food did I buy yesterday?"
  - "Give me total expenses for food on 20 June"
  - "Where did I buy hamburger from last 7 days?"

The image set I am testing with is in the folder food_receipts_scanner/uploads

### Docker

```bash
docker build -t receipt-scanner -f food_receipt_scanner/Dockerfile .
docker run -p 5000:5000 \
  -e DEEPSEEK_API_KEY=... \
  -e DEEPSEEK_MODEL=... \
  receipt-scanner
```

### CI/CD

`.github/workflows/ci.yml` builds the image and pushes it to GitHub Container Registry (`ghcr.io/<owner>/<repo>:latest`) on every push to `main`/`master`, using the built-in `GITHUB_TOKEN`.

---
