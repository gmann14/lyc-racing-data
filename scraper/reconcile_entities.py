"""Apply high-confidence entity reconciliation to an existing SQLite DB."""

from __future__ import annotations

from pathlib import Path

from scraper.load_db import DB_PATH, DatabaseLoader


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Reconcile boats/skippers in an existing SQLite database")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    args = parser.parse_args()

    loader = DatabaseLoader(Path(args.db))
    stats = loader.reconcile_entities()
    loader.close()

    print("Reconciliation complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
