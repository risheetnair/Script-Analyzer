from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="data/processed/character_dialogue_words.csv")
    ap.add_argument("--out-dir", default="reports")
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv)
    df["dialogue_words"] = df["dialogue_words"].astype(int)

    for script_id in sorted(df["script_id"].unique()):
        sdf = (
            df[df["script_id"] == script_id]
            .sort_values("dialogue_words", ascending=False)
            .head(args.top_n)
            .copy()
        )

        plt.figure()
        plt.barh(sdf["character"], sdf["dialogue_words"])
        plt.gca().invert_yaxis()
        plt.xlabel("Dialogue words")
        plt.title(f"{script_id}: Top {args.top_n} characters by dialogue")
        plt.tight_layout()

        out = out_dir / f"{script_id}_top_characters_dialogue.png"
        plt.savefig(out, dpi=200)
        plt.close()

        print(f"✅ wrote {out}")

    print(f"\nDone. Images in: {out_dir}")


if __name__ == "__main__":
    main()
