from __future__ import annotations

import argparse
from pathlib import Path
import csv
import re
from collections import Counter, defaultdict

TIME_TOKENS = {"DAY", "NIGHT", "MORNING", "EVENING", "AFTERNOON", "CONTINUOUS"}

SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT\./EXT\.|I/E)\b", re.IGNORECASE)
TRANSITION_RE = re.compile(r"^(CUT TO:|SMASH CUT:|DISSOLVE TO:|FADE (IN|OUT):)$", re.IGNORECASE)

ALLOWED_CUE_RE = re.compile(r"^[A-Z0-9 '().\-]+$")

BEAT_MARKERS = {
    "LATER",
    "MOMENTS LATER",
    "CONTINUOUS",
    "SAME",
    "TITLE",
    "INSERT",
}

def count_words(s: str) -> int:
    return len([t for t in re.split(r"\s+", s.strip()) if t])

def is_scene_heading(line: str) -> bool:
    return bool(SCENE_RE.match(line.strip()))

def is_transition(line: str) -> bool:
    return bool(TRANSITION_RE.match(line.strip()))

def normalize_cue_name(line: str) -> str:
    # "FLETCHER (O.S.)" -> "FLETCHER"
    s = line.strip().upper()
    s = s.split("(")[0].strip()
    return s

def is_speaker_cue(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    u = s.upper()

    if is_scene_heading(u) or is_transition(u):
        return False
    if ALLOWED_CUE_RE.match(u) is None:
        return False

    # Must be mostly uppercase (raw already is)
    if u != s and s.isalpha():
        # ignore lowercase words
        return False

    words = u.split()
    if len(words) > 4:
        return False
    if len(u) > 30:
        return False

    if u in BEAT_MARKERS:
        return False
    if u in TIME_TOKENS:
        return False
    if u.startswith("PAGE "):
        return False
    return True

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean-dir", default="data/clean", help="Directory containing *_clean.txt")
    ap.add_argument("--out-dir", default="data/processed", help="Where to write metrics CSVs")
    ap.add_argument("--only", default=None, help="Optional substring filter for filenames")
    args = ap.parse_args()

    clean_dir = Path(args.clean_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(clean_dir.glob("*_clean.txt"))
    if args.only:
        files = [p for p in files if args.only.lower() in p.name.lower()]

    if not files:
        print("No *_clean.txt files found.")
        return

    # Output 1: per-scene dialogue density
    scene_out = out_dir / "scene_dialogue_density.csv"
    # Output 2: per-character dialogue words
    char_out = out_dir / "character_dialogue_words.csv"

    scene_rows = []
    char_rows = []

    for path in files:
        script_id = path.stem.replace("_clean", "")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

        scene_index = -1
        scene_heading = "NO_SCENE_HEADING"

        # scene tallies
        scene_totals = defaultdict(lambda: {"action_words": 0, "dialogue_words": 0, "total_words": 0})

        # character tally
        char_words = Counter()

        in_dialogue = False
        current_speaker = None

        for ln in lines:
            s = ln.strip()

            # scene boundary
            if is_scene_heading(s):
                in_dialogue = False
                current_speaker = None
                scene_index += 1
                scene_heading = s
                continue

            # blank line ends dialogue block
            if s == "":
                in_dialogue = False
                current_speaker = None
                continue

            # transitions end dialogue
            if is_transition(s):
                in_dialogue = False
                current_speaker = None
                continue

            # speaker cue starts dialogue mode
            if is_speaker_cue(s):
                in_dialogue = True
                current_speaker = normalize_cue_name(s)
                continue

            # count words as dialogue or action
            wc = count_words(s)
            if scene_index < 0:
                # title page / pre-scene text
                # treat as action
                scene_index = 0
                if scene_heading == "NO_SCENE_HEADING":
                    scene_heading = "NO_SCENE_HEADING"

            key = (script_id, scene_index, scene_heading)

            if in_dialogue and current_speaker:
                scene_totals[key]["dialogue_words"] += wc
                char_words[current_speaker] += wc
            else:
                scene_totals[key]["action_words"] += wc

            scene_totals[key]["total_words"] += wc

        # write collected rows
        for (sid, idx, heading), d in scene_totals.items():
            total = d["total_words"]
            dialog = d["dialogue_words"]
            action = d["action_words"]
            ratio = (dialog / total) if total else 0.0
            scene_rows.append({
                "script_id": sid,
                "scene_index": idx,
                "scene_heading": heading,
                "total_words": total,
                "dialogue_words": dialog,
                "action_words": action,
                "dialogue_ratio": f"{ratio:.4f}",
            })

        for speaker, words in char_words.most_common():
            char_rows.append({
                "script_id": script_id,
                "character": speaker,
                "dialogue_words": words,
            })

        print(f"✅ analyzed {path.name}: scenes={max(scene_index,0)+1} speakers={len(char_words)}")

    # sort for readability
    scene_rows.sort(key=lambda r: (r["script_id"], int(r["scene_index"])))
    char_rows.sort(key=lambda r: (r["script_id"], -int(r["dialogue_words"])))

    with scene_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(scene_rows[0].keys()))
        w.writeheader()
        w.writerows(scene_rows)

    with char_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(char_rows[0].keys()))
        w.writeheader()
        w.writerows(char_rows)

    print(f"\nWrote:\n- {scene_out}\n- {char_out}")

if __name__ == "__main__":
    main()
