# tests/test_normalize.py
from __future__ import annotations

from src.normalize import normalize_text


def test_removes_page_numbers_and_form_feed():
    raw = "\f11\n\n37\nINT. ROOM - DAY\nSome action.\n"
    cleaned, stats = normalize_text(raw)
    assert "\f" not in cleaned
    assert "37\n" not in cleaned
    assert stats.removed_form_feed_lines >= 1
    assert stats.removed_page_numbers >= 1


def test_preserves_scene_heading_and_character_cue_boundaries():
    raw = (
        "INT. WARSAW AIRPORT - MORNING\n"
        "The boys walk through the airport, both exhausted from the\n"
        "flight.\n"
        "DAVID\n"
        "You wanna get some breakfast?\n"
    )
    cleaned, _ = normalize_text(raw, enable_split_word_repair=False)

    # Scene heading should remain its own line
    assert "INT. WARSAW AIRPORT - MORNING\n" in cleaned

    # Character cue should remain its own line
    assert "\nDAVID\n" in cleaned


def test_unwraps_wrapped_lines_inside_action_block():
    raw = (
        "INT. CAR - MORNING\n"
        "The boys are in the car, heading into town. Benji is staring\n"
        "out the window; David is staring at his phone, AirPods in his\n"
        "ears.\n"
    )
    cleaned, _ = normalize_text(raw, enable_split_word_repair=False)

    # Action lines should be merged into one paragraph line (between boundaries)
    assert "Benji is staring out the window; David is staring at his phone" in cleaned


def test_hyphen_join():
    raw = (
        "BENJI\n"
        "Hey, there’s our guy-\n"
        "Benji points to a Polish DRIVER holding a sign.\n"
    )
    cleaned, _ = normalize_text(raw, enable_split_word_repair=False)
    assert "our guy-Benji points" in cleaned
