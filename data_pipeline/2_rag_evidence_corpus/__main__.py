from __future__ import annotations

import argparse

from .corpus import build_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="FoodTrust regulatory RAG")
    parser.add_argument("command", choices=["ingest"])
    args = parser.parse_args()
    if args.command == "ingest":
        print(f"Indexed {build_corpus()} evidence chunks.")
if __name__ == "__main__":
    main()
