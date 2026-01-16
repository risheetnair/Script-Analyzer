from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Tuple

from .patterns import has_form_feed, is_page_number, is_hard_boundary

INVISIBLE = "\ufeff\u200b\u00a0"

def sanitize_line(s: str) -> str:
    # Remove invisible chars anywhere, and trim ends
    return s.translate({ord(ch): None for ch in INVISIBLE}).strip()


@dataclass
class NormalizeStats:
    """Basic instrumentation for the normalization pipeline."""

    lines_in: int = 0
    lines_out: int = 0
    removed_page_numbers: int = 0
    removed_form_feed_lines: int = 0
    merged_lines: int = 0


# -----------------
# Core helpers
# -----------------

def canonicalize_lines(raw_text: str) -> List[str]:
    """Normalize line endings and strip trailing whitespace."""
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    return [ln.rstrip() for ln in raw_text.split("\n")]


def remove_pdf_artifacts(lines: List[str], stats: NormalizeStats) -> List[str]:
    """Drop obvious PDF extraction artifacts (page numbers, form-feed lines)."""
    out: List[str] = []
    for ln in lines:
        if has_form_feed(ln):
            stats.removed_form_feed_lines += 1
            continue
        if is_page_number(ln):
            stats.removed_page_numbers += 1
            continue
        out.append(ln)
    return out


# -----------------
# Structure injection
# -----------------

def inject_structure_newlines(lines: List[str], stats: NormalizeStats) -> List[str]:
    """\
    Insert newlines so that (some) screenplay structure tokens land on their own lines.

    Targets:
    - Beat markers: AND ANOTHER:, ANOTHER MESSAGE:
    - Scene heading starters: INT., EXT., INT./EXT., I/E (when embedded mid-line)
    - Character cues embedded mid-line (ALL CAPS short tokens)

    Note: this step runs *before* unwrapping so these tokens become hard boundaries.
    """

    # Beat markers: keep the full marker together
    beat_markers = re.compile(r"\b(AND ANOTHER:|ANOTHER MESSAGE:)\s*", re.IGNORECASE)

    # Scene heading starters that appear after punctuation/colon/dashes/quotes
    scene_emb1 = re.compile(r"([.!?:]|—|-)\s+(INT\.|EXT\.|INT\./EXT\.|I/E)\b", re.IGNORECASE)
    scene_emb2 = re.compile(r"([\"\)\]])\s+(INT\.|EXT\.|INT\./EXT\.|I/E)\b", re.IGNORECASE)

    # Embedded character cue: punctuation + ALLCAPS cue (1–3 tokens) + space
    cue_emb = re.compile(
        r"([.!?:]|—|-)\s+([A-Z][A-Z'().\-]*(?:\s+[A-Z][A-Z'().\-]*){0,2})\s+"
    )

    out: List[str] = []
    for ln in lines:
        if not ln.strip():
            out.append(ln)
            continue

        ln2 = beat_markers.sub(r"\n\1\n", ln)
        ln2 = scene_emb1.sub(r"\1\n\2", ln2)
        ln2 = scene_emb2.sub(r"\1\n\2", ln2)

        def _cue_repl(m: re.Match[str]) -> str:
            return f"{m.group(1)}\n{m.group(2)}\n"

        ln2 = cue_emb.sub(_cue_repl, ln2)

        # Expand any injected newlines into separate lines
        parts = [p.strip() for p in ln2.split("\n") if p is not None]
        out.extend([p for p in parts if p != ""])

    return out


def merge_scene_heading_chunks(lines: List[str], stats: NormalizeStats) -> List[str]:
    """\
    Merge broken scene headings like:

      EXT.
      BQE
      - DAY

    into:
      EXT. BQE - DAY

    Stops merging once a time-of-day token is included.
    """

    time_tokens = {"DAY", "NIGHT", "MORNING", "EVENING", "AFTERNOON", "CONTINUOUS"}
    starters = {"INT.", "EXT.", "INT./EXT.", "I/E"}

    out: List[str] = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if cur.upper() not in starters:
            out.append(lines[i])
            i += 1
            continue

        parts = [cur]
        j = i + 1
        while j < len(lines):
            nxt = lines[j].strip()
            if nxt == "":
                break

            parts.append(nxt)
            nxt_upper = nxt.upper()

            # stop once we see a time token anywhere on the line
            if any(tok in nxt_upper.split() for tok in time_tokens) or nxt_upper in time_tokens:
                j += 1
                break

            # safety: headings shouldn't consume many lines
            if len(parts) >= 6:
                j += 1
                break

            j += 1

        merged = " ".join(parts)
        merged = " ".join(merged.split())
        out.append(merged)
        i = j

    return out


def split_heading_by_time_token(lines: List[str], stats: NormalizeStats) -> List[str]:
    """\
    Force scene headings onto their own line when followed by action text.

    Example:
      EXT. BQE - DAY Following David...
    ->
      EXT. BQE - DAY
      Following David...
    """

    time_tokens = [
        " - DAY",
        " - NIGHT",
        " - MORNING",
        " - EVENING",
        " - AFTERNOON",
        " - CONTINUOUS",
    ]

    out: List[str] = []
    for ln in lines:
        s = ln.strip()
        upper = s.upper()

        if "INT." in upper or "EXT." in upper or "INT./EXT." in upper or "I/E" in upper:
            for tok in time_tokens:
                idx = upper.find(tok)
                if idx == -1:
                    continue

                cut = idx + len(tok)
                head = s[:cut].strip()
                rest = s[cut:].strip()

                if rest:
                    out.append(head)
                    out.append(rest)
                else:
                    out.append(head)
                break
            else:
                out.append(ln)
        else:
            out.append(ln)

    return out


# -----------------
# Unwrap paragraphs
# -----------------

def unwrap_within_blocks(lines: List[str], stats: NormalizeStats) -> List[str]:
    out: List[str] = []
    buffer: List[str] = []

    def flush():
        nonlocal buffer
        if buffer:
            out.append(_join_buffer(buffer, stats))
            buffer = []

    for ln in lines:
        s = sanitize_line(ln)

        if s == "":
            flush()
            out.append("")
            continue

        if is_hard_boundary(s):
            flush()
            out.append(s)
            continue

        buffer.append(s)

    flush()
    return out





def _join_buffer(chunks: List[str], stats: NormalizeStats) -> str:
    """Join lines into a paragraph, preserving hyphen joins."""
    joined = chunks[0].strip() if chunks else ""
    for nxt in chunks[1:]:
        nxt_s = nxt.strip()
        if not nxt_s:
            continue
        if joined.endswith("-"):
            joined = joined + nxt_s
        else:
            joined = joined + " " + nxt_s
        stats.merged_lines += 1
    return joined


def collapse_blank_lines(lines: List[str]) -> List[str]:
    """Collapse runs of blank lines to a single blank line."""
    out: List[str] = []
    prev_blank = False
    for ln in lines:
        blank = (ln.strip() == "")
        if blank and prev_blank:
            continue
        out.append("" if blank else ln)
        prev_blank = blank
    return out


# -----------------
# Public API
# -----------------

def normalize_text(raw_text: str) -> Tuple[str, NormalizeStats]:
    stats = NormalizeStats()

    lines = canonicalize_lines(raw_text)
    stats.lines_in = len(lines)

    lines = remove_pdf_artifacts(lines, stats)

    lines = collapse_blank_lines([ln.rstrip() for ln in lines])

    stats.lines_out = len(lines)
    cleaned = "\n".join(lines).strip() + "\n"
    return cleaned, stats


