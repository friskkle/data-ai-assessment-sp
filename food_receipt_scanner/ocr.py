import re
from datetime import date

import cv2
import pytesseract

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# A price token: optional "$", 1-3 digits, then a decimal point and 2 digits,
# tolerating OCR quirks like "$33 .54" (a space inside the number).
_PRICE_TOKEN = r"\$?\s*\d{1,3}(?:\s*[.,]\s*\d{2})"

# Words that are receipt structure, not food items.
_SKIP = {
    "total", "subtotal", "sub total", "tax", "vat", "change", "cash",
    "card", "credit", "debit", "balance", "due", "amount", "tendered",
    "tip", "visa", "mastercard", "items", "qty", "price", "thank",
}

# Line hints that mark a total/subtotal line (including OCR misspellings).
_TOTAL_HINTS = ("total", "subtotal", "sub total", "subotal", "amount due", "grand total")


def _preprocess(image_path, target_long_side=1800):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"could not read image: {image_path}")

    h, w = img.shape[:2]
    if max(h, w) < target_long_side:
        scale = target_long_side / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )


def extract_text(image_path):
    """OCR a receipt image into raw text."""
    gray = _preprocess(image_path)
    return pytesseract.image_to_string(gray, config="--psm 6")


def _clean_price(token):
    return float(token.replace("$", "").replace(",", ".").replace(" ", ""))


def _make_iso(y, mo, d):
    if 1 <= mo <= 12 and 1 <= d <= 31:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def _extract_date(text):
    # numeric: 20/06/2026, 20-06-2026, 20.06.2026 (DD/MM) or 05/24/2025 (MM/DD)
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", text)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        iso = _make_iso(y, b, a) or _make_iso(y, a, b)
        if iso:
            return iso
    # 20 Jun 2026 / 20 June 2026
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})[.,]?\s+(\d{4})\b", text)
    if m:
        d, mo, y = int(m.group(1)), m.group(2)[:3].lower(), int(m.group(3))
        if mo in _MONTHS and 1 <= d <= 31:
            return f"{y:04d}-{_MONTHS[mo]:02d}-{d:02d}"
    # Jun 20, 2026
    m = re.search(r"\b([A-Za-z]{3,9})[.,]?\s+(\d{1,2}),?\s+(\d{4})\b", text)
    if m:
        mo, d, y = m.group(1)[:3].lower(), int(m.group(2)), int(m.group(3))
        if mo in _MONTHS and 1 <= d <= 31:
            return f"{y:04d}-{_MONTHS[mo]:02d}-{d:02d}"
    return date.today().isoformat()  # fallback to today if no date found


def parse_receipt(text):
    """Turn raw OCR text into a structured receipt dict."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    store = lines[0]
    receipt_date = _extract_date(text)
    total = None
    items = []

    for ln in lines:
        low = ln.lower()

        if any(hint in low for hint in _TOTAL_HINTS):
            prices = re.findall(_PRICE_TOKEN, ln)
            if prices:
                total = _clean_price(prices[-1])
            continue

        m = re.search(r"^(.*?)\s+(" + _PRICE_TOKEN + r")\s*$", ln)
        if m:
            name = m.group(1).strip().rstrip("$").strip()
            price = _clean_price(m.group(2))
            name_low = name.lower()
            if name and not any(w in name_low for w in _SKIP):
                items.append({"name": name, "price": price, "quantity": 1})

    if total is None:
        total = round(sum(it["price"] for it in items), 2)

    return {
        "store": store,
        "date": receipt_date,
        "total": total,
        "items": items,
        "raw_text": text,
    }
