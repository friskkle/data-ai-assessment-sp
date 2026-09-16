"""
Turn text into a fixed-size vector by counting character bigrams.

Each text is normalized (lowercase and only a single whitespace), then we count how many
times each pair of adjacent characters (bigram) appears. There is one
dimension per possible bigram over a fixed alphabet, so cosine similarity
measures how much two texts share the same letter-pair structure.
"""

DEFAULT_FIELDS = (
    "First Name",
    "Last Name",
    "Company",
    "City",
    "Country",
    "Email",
    "Website",
)

ALPHABET = " abcdefghijklmnopqrstuvwxyz0123456789"
_CHAR_DIM = len(ALPHABET)
DIM = _CHAR_DIM * _CHAR_DIM # dimension of the vector space will be 37*37 = 1369
_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}


def _normalize(text):
    return " ".join(str(text).lower().split())


def embed_text(text):
    """Return a bigram-count vector for the input text."""
    text = _normalize(text)
    counts = [0.0] * DIM
    for a, b in zip(text, text[1:]):
        ia = _INDEX.get(a)
        ib = _INDEX.get(b)
        if ia is not None and ib is not None:
            counts[ia * _CHAR_DIM + ib] += 1
    return counts


def embed_row(row, fields=DEFAULT_FIELDS):
    """Embed a csv row (dict) by concatenating the selected text fields."""
    parts = [str(row[f]) for f in fields if row.get(f)]
    return embed_text(" ".join(parts))
