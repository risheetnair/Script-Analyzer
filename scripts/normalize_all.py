from __future__ import annotations

import argparse
from pathlib import Path

from src.normalize import normalize_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize raw screenplay text files.")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory containing raw .txt files")
    parser.add_argument("--clean-dir", default="data/clean", help="Directory to write cleaned .txt files")
    parser.add_argument("--only", default=None, help="Optional substring filter (e.g., 'whiplash')")
    parser.add_argument("--no-split-repair", action="store_true", help="Disable split-word repairs")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    clean_dir = Path(args.clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(raw_dir.glob("*.txt"))
    if args.only:
        raw_files = [p for p in raw_files if args.only.lower() in p.name.lower()]

    if not raw_files:
        print("No raw .txt files found. (Reminder: data/raw/ is gitignored.)")
        return

    for path in raw_files:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        cleaned, stats = normalize_text(raw_text, enable_split_word_repair=not args.no_split_repair)

        out_path = clean_dir / f"{path.stem}_clean.txt"
        out_path.write_text(cleaned, encoding="utf-8")

        print(f"\n✅ {path.name} -> {out_path.name}")
        print(f"  lines_in={stats.lines_in} lines_out={stats.lines_out}")
        print(f"  removed_page_numbers={stats.removed_page_numbers} removed_form_feed_lines={stats.removed_form_feed_lines}")
        print(f"  merged_lines={stats.merged_lines} split_word_repairs={stats.split_word_repairs}")


if __name__ == "__main__":
    main()
