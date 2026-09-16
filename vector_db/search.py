import argparse

from .embedding import embed_text
from .vector_db import HashDB


def main():
    parser = argparse.ArgumentParser(
        description="Query a built vector index by cosine similarity."
    )
    parser.add_argument("query", help="text query any attribute of the customer, e.g. 'Jared Jarvis Congo'")
    parser.add_argument("--index-dir", default="data/index", help="index directory")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    index = HashDB.load(args.index_dir)
    query_vector = embed_text(args.query)
    results = index.search(query_vector, top_k=args.top_k)

    print(f"Top {len(results)} matches for {args.query!r}\n")
    for rank, (score, payload) in enumerate(results, start=1):
        print(
            f"{rank}. score={score:.4f}  "
            f"{payload.get('Name')} | {payload.get('Company')} | "
            f"{payload.get('City')}, {payload.get('Country')}"
        )


if __name__ == "__main__":
    main()
