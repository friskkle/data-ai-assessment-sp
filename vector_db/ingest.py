import argparse
import csv
import time

from .embedding import DEFAULT_FIELDS, embed_row
from .vector_db import HashDB


def build_index(csv_path, index_dir, limit=None, fields=DEFAULT_FIELDS):
    index = HashDB()
    count = 0

    # Stream the file row by row so memory stays flat.
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            vector = embed_row(row, fields=fields)
            payload = {
                "Customer Id": row.get("Customer Id"),
                "Name": f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                "Company": row.get("Company"),
                "City": row.get("City"),
                "Country": row.get("Country"),
                "Email": row.get("Email"),
                "Website": row.get("Website"),
                "Subscription Date": row.get("Subscription Date"),
            }
            index.add_vector(vector, payload)
            count += 1
            if limit and count >= limit:
                break

    return index, count


def main():
    parser = argparse.ArgumentParser(
        description="Build a cosine-similarity vector index from a customer CSV."
    )
    parser.add_argument("--csv", required=True, help="path to the source CSV")
    parser.add_argument("--index-dir", default="data/index", help="output directory")
    parser.add_argument("--limit", type=int, default=None, help="max rows to index")
    args = parser.parse_args()

    start = time.time()
    index, count = build_index(args.csv, args.index_dir, limit=args.limit)
    index.save(args.index_dir)
    elapsed = time.time() - start

    print(f"Indexed {count} rows -> {args.index_dir} (dim={index.dim}) in {elapsed:.2f}s")
    print("Wrote vectors.bin, payloads.jsonl, meta.json")


if __name__ == "__main__":
    main()
