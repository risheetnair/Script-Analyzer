from __future__ import annotations

import argparse
from pathlib import Path

import csv

from src.parser import parse_script


def blocks_to_csv(blocks, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "script_id",
        "scene_index",
        "scene_heading",
        "block_index",
        "block_type",
        "character",
        "word_count",
        "text",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for b in blocks:
            writer.writerow({
                "script_id": b.script_id,
                "scene_index": b.scene_index,
                "scene_heading": b.scene_heading,
                "block_index": b.block_index,
                "block_type": b.block_type,
                "character": b.character or "",
                "word_count": b.word_count,
                "text": b.text,
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse normalized screenplay text into blocks.")
    parser.add_argument("--clean-dir", default="data/clean", help="Directory containing *_clean.txt files")
    parser.add_argument("--out-dir", default="data/processed", help="Directory to write CSV outputs")
    parser.add_argument("--only", default=None, help="Optional substring filter (e.g., 'whiplash')")
    args = parser.parse_args()

    clean_dir = Path(args.clean_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_files = sorted(clean_dir.glob("*_clean.txt"))
    if args.only:
        clean_files = [p for p in clean_files if args.only.lower() in p.name.lower()]

    if not clean_files:
        print("No *_clean.txt files found in data/clean/.")
        return

    for path in clean_files:
        script_id = path.stem.replace("_clean", "")
        cleaned_text = path.read_text(encoding="utf-8", errors="replace")

        result = parse_script(cleaned_text, script_id=script_id)
        blocks = result["blocks"]
        stats = result["stats"]

        out_path = out_dir / f"{script_id}_blocks.csv"
        blocks_to_csv(blocks, out_path)

        print(f"\n✅ {path.name} -> {out_path.name}")
        print(f"  scenes={stats.scenes} blocks={stats.blocks} dialogue={stats.dialogue_blocks} action={stats.action_blocks}")


if __name__ == "__main__":
    main()
