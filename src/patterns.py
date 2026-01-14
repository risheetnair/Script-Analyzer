from __future__ import annotations

import re
from dataclasses import dataclass

SCENE_HEADING_RE = re.compile(r"^\s*(INT\.|EXT\.|INT\./EXT\.|I/E)\b", re.IGNORECASE)
PAGE_NUMBER_RE = re.compile(r"^\s*\d+\s*$")
FORM_FEED_RE = re.compile(r"[\f]") # form feed character

# Transition cues:
TRANSITION_RE = re.compile(r"^\s*[A-Z0-9 '().-]+TO:\s*$")

# Candidate character cues:
# - mostly uppercase
# - short
# - may include modifiers like (O.S.), (PRE-LAP)
CHAR_CUE_ALLOWED_RE = re.compile(r"^[A-Z0-9 '().\-]+$")

CHAR_CUE_BLOCKLIST = frozenset(
    {
        "AFTERNOON",
        "DAWN",
        "DAY",
        "DUSK",
        "EVENING",
        "LATER",
        "MIDNIGHT",
        "MOMENTS LATER",
        "MORNING",
        "NIGHT",
        "NOON",
        "SAME TIME",
        "SUNRISE",
        "SUNSET",
    }
)

@dataclass(frozen=True)
class BoundaryFlags:
    is_blank: bool
    is_scene_heading: bool
    is_character_cue: bool
    is_transition: bool


def is_blank(line: str) -> bool:
    return line.strip() == ""


def is_page_number(line: str) -> bool:
    return PAGE_NUMBER_RE.match(line) is not None


def has_form_feed(line: str) -> bool:
    return FORM_FEED_RE.search(line) is not None


def is_scene_heading(line: str) -> bool:
    return SCENE_HEADING_RE.match(line) is not None


def is_transition(line: str) -> bool:
    return TRANSITION_RE.match(line.strip()) is not None


def is_character_cue(line: str) -> bool:
    """
    Heuristic (v1):
    - mostly uppercase letters/numbers/spaces/punct
    - short (by word count and length)
    - not a scene heading
    - not a transition
    """
    s = line.strip()
    if not s:
        return False
    if is_scene_heading(s) or is_transition(s):
        return False
    if CHAR_CUE_ALLOWED_RE.match(s) is None:
        return False
    
    words = s.split()
    if len(words) > 4:
        return False
    if len(s) > 30:
        return False

    # Avoid treating common non-cue words as cues
    if s in CHAR_CUE_BLOCKLIST:
        return False

    # Looks cue-like
    return True


def strip_character_modifiers(cue_line: str) -> str:
    """
    Convert: 'FLETCHER (PRE-LAP)' -> 'FLETCHER'
    Convert: 'JIM (O.S.)' -> 'JIM'
    """
    s = cue_line.strip()
    # Split off anything starting at first ' (' or '('
    base = re.split(r"\s*\(", s, maxsplit=1)[0]
    return base.strip()


def boundary_flags(line: str) -> BoundaryFlags:
    """
    Convenience: classify boundaries in one place.
    """
    return BoundaryFlags(
        is_blank=is_blank(line),
        is_scene_heading=is_scene_heading(line),
        is_character_cue=is_character_cue(line),
        is_transition=is_transition(line),
    )


def is_hard_boundary(line: str) -> bool:
    f = boundary_flags(line)
    return f.is_blank or f.is_scene_heading or f.is_character_cue or f.is_transition
