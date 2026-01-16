from __future__ import annotations

from src.parser import parse_script


def test_parses_scene_heading_action_and_dialogue_blocks():
    cleaned = (
        "INT. ROOM - DAY\n"
        "ALEX sits at a table.\n"
        "\n"
        "ALEX\n"
        "I don't know what you're talking about.\n"
        "\n"
        "JAMIE\n"
        "(quiet)\n"
        "You never do.\n"
        "\n"
    )
    result = parse_script(cleaned, script_id="sample")
    blocks = result["blocks"]

    # Expect: action block + dialogue block + dialogue block
    assert len(blocks) == 3
    assert blocks[0].block_type == "ACTION"
    assert blocks[1].block_type == "DIALOGUE"
    assert blocks[1].character == "ALEX"
    assert "I don't know" in blocks[1].text

    assert blocks[2].block_type == "DIALOGUE"
    assert blocks[2].character == "JAMIE"
    assert "(quiet)" in blocks[2].text


def test_character_modifiers_are_stripped():
    cleaned = (
        "INT. HALLWAY - NIGHT\n"
        "\n"
        "FLETCHER (O.S.)\n"
        "Not my tempo.\n"
        "\n"
    )
    result = parse_script(cleaned, script_id="sample")
    blocks = result["blocks"]
    assert len(blocks) == 1
    assert blocks[0].character == "FLETCHER"
