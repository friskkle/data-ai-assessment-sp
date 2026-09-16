import json
import os
from array import array

from .cosine_similarity import cosine_similarity


class HashDB:
    """
    Vector database backed by feature-hashed vectors with cosine similarity search.

    Vectors and their payloads are kept in memory; a query is scored against
    every stored vector using the hand-written cosine similarity and the top-k
    is returned. Indexes can be saved to and loaded from disk (vectors.bin +
    payloads.jsonl + meta.json) so a build step is separate from query time.
    """

    def __init__(self, dim=None):
        self.dim = dim
        self.vectors = []
        self.payloads = []

    def add_vector(self, vector, payload):
        if self.dim is None:
            self.dim = len(vector)
        if len(vector) != self.dim:
            raise ValueError(
                f"expected vector of length {self.dim}, got {len(vector)}"
            )
        self.vectors.append(list(vector))
        self.payloads.append(payload)

    def search(self, query_vector, top_k=5):
        if len(query_vector) != self.dim:
            raise ValueError(
                f"query vector of length {len(query_vector)} does not match dim {self.dim}"
            )
        similarities = [
            (cosine_similarity(query_vector, v), p)
            for v, p in zip(self.vectors, self.payloads)
        ]
        similarities.sort(key=lambda pair: pair[0], reverse=True)
        return similarities[:top_k]

    def save(self, directory):
        os.makedirs(directory, exist_ok=True)

        flat = array("d")
        for vec in self.vectors:
            flat.extend(vec)
        with open(os.path.join(directory, "vectors.bin"), "wb") as fh:
            flat.tofile(fh)

        with open(os.path.join(directory, "payloads.jsonl"), "w", encoding="utf-8") as fh:
            for payload in self.payloads:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

        with open(os.path.join(directory, "meta.json"), "w", encoding="utf-8") as fh:
            json.dump({"dim": self.dim, "count": len(self.vectors)}, fh)

    @classmethod
    def load(cls, directory):
        with open(os.path.join(directory, "meta.json"), encoding="utf-8") as fh:
            meta = json.load(fh)

        db = cls(meta["dim"])

        flat = array("d")
        with open(os.path.join(directory, "vectors.bin"), "rb") as fh:
            flat.fromfile(fh, meta["count"] * meta["dim"])
        for i in range(meta["count"]):
            start = i * meta["dim"]
            db.vectors.append(list(flat[start:start + meta["dim"]]))

        with open(os.path.join(directory, "payloads.jsonl"), encoding="utf-8") as fh:
            db.payloads = [json.loads(line) for line in fh]

        return db
