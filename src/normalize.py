from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List, Tuple

from .patterns import has_form_feed, is_page_number, is_hard_boundary


@dataclass
class NormalizeStats:
    lines_in: int = 0
    lines_out: int = 0
    removed_page_numbers: int = 0
    removed_form_feed_lines: int = 0
    merged_lines: int = 0
    split_word_repairs: int = 0


_COMMON_SHORT_WORDS = {
    "a",
    "i",
    "am",
    "an",
    "as",
    "at",
    "be",
    "by",
    "do",
    "go",
    "he",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "no",
    "of",
    "on",
    "or",
    "so",
    "to",
    "up",
    "us",
    "we",
}

_SINGLE_LETTER_RUN_RE = re.compile(r"\b(?:[a-z]\s+){2,}[a-z]\b")
_SINGLE_LEFT_RE = re.compile(r"\b([A-Za-z])\s+([A-Za-z]{2,})\b")
_SINGLE_RIGHT_RE = re.compile(r"\b([A-Za-z]{2,})\s+([A-Za-z])\b")
_TWO_PART_RE = re.compile(r"\b([A-Za-z]{2,})\s+([A-Za-z]{2,})\b")


def canonicalize_lines(raw_text: str) -> List[str]:
    """
    Normalize line endings, strip trailing whitespace.
    Keep leading whitespace intact (might be useful later).
    """
    # Replace Windows newlines just in case
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw_text.split("\n")
    return [ln.rstrip() for ln in lines]


def remove_pdf_artifacts(lines: List[str], stats: NormalizeStats) -> List[str]:
    """
    Drop page numbers and lines containing form-feed markers.
    """
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


def repair_split_words_in_line(line: str, stats: NormalizeStats) -> str:
    """
    Conservative split-word repair for cases like:
    - 'sl ept' -> 'slept'
    - 'Decla re' -> 'Declare'
    """
    if " " not in line:
        return line

    original = line
    line = _SINGLE_LETTER_RUN_RE.sub(lambda m: m.group(0).replace(" ", ""), line)

    def _join_single_left(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(2)
        if left.lower() in _COMMON_SHORT_WORDS:
            return match.group(0)
        return left + right

    def _join_single_right(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(2)
        if right.lower() in _COMMON_SHORT_WORDS:
            return match.group(0)
        return left + right

    line = _SINGLE_LEFT_RE.sub(_join_single_left, line)
    line = _SINGLE_RIGHT_RE.sub(_join_single_right, line)

    def _join_two_parts(match: re.Match[str]) -> str:
        left = match.group(1)
        right = match.group(2)
        if len(left) > 3 and len(right) > 3:
            return match.group(0)
        if left.islower() and left in _COMMON_SHORT_WORDS:
            return match.group(0)
        if right.islower() and right in _COMMON_SHORT_WORDS:
            return match.group(0)
        return left + right

    line = _TWO_PART_RE.sub(_join_two_parts, line)

    if line != original:
        stats.split_word_repairs += 1
    return line


def unwrap_within_blocks(lines: List[str], stats: NormalizeStats) -> List[str]:
    """
    Merge wrapped lines inside non-boundary blocks into single paragraphs.
    Preserve boundaries (blank lines, scene headings, character cues, transitions).
    """
    out: List[str] = []
    buffer: List[str] = []

    def flush_buffer():
        nonlocal buffer
        if buffer:
            out.append(_join_buffer(buffer, stats))
            buffer = []

    for ln in lines:
        if is_hard_boundary(ln):
            flush_buffer()
            out.append(ln.strip() if ln.strip() == "" else ln)  # keep blank lines
            continue

        # Non-boundary line: accumulate
        # Optionally repair split words here or earlier
        buffer.append(ln)

    flush_buffer()
    return out


def _join_buffer(chunks: List[str], stats: NormalizeStats) -> str:
    """
    Join a list of lines into one paragraph.
    - Add spaces between lines
    - If previous line ends with '-', merge without an extra space
    """
    if not chunks:
        return ""

    joined = chunks[0].strip()
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
    """
    Optional polish: collapse runs of blank lines to a single blank line.
    """
    out: List[str] = []
    prev_blank = False
    for ln in lines:
        blank = (ln.strip() == "")
        if blank and prev_blank:
            continue
        out.append("" if blank else ln)
        prev_blank = blank
    return out


def normalize_text(raw_text: str, enable_split_word_repair: bool = False) -> Tuple[str, NormalizeStats]:
    stats = NormalizeStats()
    lines = canonicalize_lines(raw_text)
    stats.lines_in = len(lines)

    lines = remove_pdf_artifacts(lines, stats)

    if enable_split_word_repair:
        repaired: List[str] = []
        for ln in lines:
            repaired.append(repair_split_words_in_line(ln, stats))
        lines = repaired

    lines = unwrap_within_blocks(lines, stats)
    lines = collapse_blank_lines(lines)

    stats.lines_out = len(lines)
    cleaned = "\n".join(lines).strip() + "\n"
    return cleaned, stats
