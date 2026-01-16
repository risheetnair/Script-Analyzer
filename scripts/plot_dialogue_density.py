from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene-csv", default="data/processed/scene_dialogue_density.csv")
    ap.add_argument("--blocks-csv", default=None, help="Optional: block-level CSV if you have it. Not required.")
    ap.add_argument("--out-dir", default="reports")
    ap.add_argument("--min-total-words", type=int, default=200, help="Filter tiny scenes")
    ap.add_argument("--rolling-window-scenes", type=int, default=5, help="Rolling average window (in scenes)")
    args = ap.parse_args()

    scene_path = Path(args.scene_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(scene_path)
    df["scene_index"] = df["scene_index"].astype(int)
    df["total_words"] = df["total_words"].astype(int)
    df["dialogue_words"] = df["dialogue_words"].astype(int)
    df["action_words"] = df["action_words"].astype(int)
    df["dialogue_ratio"] = df["dialogue_ratio"].astype(float)

    # Keep scenes that have enough words (removes tiny taxi slugs etc.)
    df = df[df["total_words"] >= args.min_total_words].copy()

    df_plot = df[df["scene_heading"] != "NO_SCENE_HEADING"].copy()

    for script_id in sorted(df["script_id"].unique()):
        sdf = df_plot[df_plot["script_id"] == script_id].sort_values("scene_index").copy()

        if sdf.empty:
            sdf = df[df["script_id"] == script_id].sort_values("scene_index").copy()

        # Rolling smoothing (scene-based)
        sdf["rolling_ratio"] = sdf["dialogue_ratio"].rolling(
            window=args.rolling_window_scenes, min_periods=1
        ).mean()

        # --- Plot 1: dialogue ratio per scene (raw + rolling) ---
        plt.figure()
        plt.plot(sdf["scene_index"], sdf["dialogue_ratio"], marker="o")
        plt.plot(sdf["scene_index"], sdf["rolling_ratio"], marker="o")
        plt.xlabel("Scene index")
        plt.ylabel("Dialogue ratio (dialogue_words / total_words)")
        plt.title(f"{script_id}: Dialogue density by scene")
        plt.tight_layout()
        out1 = out_dir / f"{script_id}_dialogue_density_by_scene.png"
        plt.savefig(out1, dpi=200)
        plt.close()

        print(f"✅ wrote {out1}")

    print(f"\nDone. Images in: {out_dir}")


if __name__ == "__main__":
    main()
