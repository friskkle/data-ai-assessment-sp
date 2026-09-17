import os

# Minimal .env loader (no dotenv dependency). Checks the current directory and
# the package directory, so the key works whether .env sits at the repo root or
# next to this file.
def _load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_load_dotenv(".env")
_load_dotenv(os.path.join(BASE_DIR, ".env"))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = os.environ.get(
    "DEEPSEEK_URL", "https://api.deepseek.com/chat/completions"
)

DB_PATH = os.environ.get("RECEIPT_DB", os.path.join(BASE_DIR, "receipts.db"))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"}
