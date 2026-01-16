from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .patterns import (
    is_blank,
    is_scene_heading,
    is_character_cue,
    strip_character_modifiers,
)


@dataclass
class Block:
    script_id: str
    scene_index: int
    scene_heading: str
    block_index: int
    block_type: str  # "ACTION" or "DIALOGUE"
    character: Optional[str]  # only for DIALOGUE
    text: str
    word_count: int


@dataclass
class ParseStats:
    scenes: int = 0
    blocks: int = 0
    dialogue_blocks: int = 0
    action_blocks: int = 0


def count_words(text: str) -> int:
    """
    Basic token count. You can improve later (e.g., strip punctuation).
    """
    # TODO: refine tokenization if needed
    tokens = [t for t in text.split() if t.strip()]
    return len(tokens)


def is_parenthetical(line: str) -> bool:
    s = line.strip()
    return s.startswith("(") and s.endswith(")") and len(s) >= 2


class ScriptParser:
    """
    Block-based screenplay parser (v1).

    Assumptions:
    - Input text is normalized (unwrapped) and has structure-preserving boundaries.
    - Scene headings, character cues, and blank lines can be reliably detected.
    """

    def __init__(self, script_id: str):
        self.script_id = script_id
        self.seen_first_scene_heading = False

        # Current scene state
        self.scene_index = -1
        self.scene_heading = ""

        # Current buffer state
        self.block_index = 0
        self.buffer_type: Optional[str] = None  # "ACTION" or "DIALOGUE"
        self.buffer_character: Optional[str] = None
        self.buffer_lines: List[str] = []

        # Outputs
        self.blocks: List[Block] = []

        # Stats
        self.stats = ParseStats()

    def parse(self, cleaned_text: str) -> List[Block]:
        lines = cleaned_text.splitlines()

        for line in lines:
            self._consume_line(line)

        # Flush anything left at EOF
        self._flush_buffer()
        self._finalize_stats()
        return self.blocks

    def _consume_line(self, line: str) -> None:
        """
        Main state machine.
        """
        if is_scene_heading(line):
            self.seen_first_scene_heading = True
            self._flush_buffer()
            self._start_new_scene(line)
            return


        if is_character_cue(line):
            # This prevents false "speakers" like the script title from becoming dialogue.
            if not self.seen_first_scene_heading:
                if self.buffer_type is None:
                    self._start_action_block()
                self.buffer_lines.append(line.strip())
                return

            self._flush_buffer()
            speaker = strip_character_modifiers(line)
            self._start_dialogue_block(speaker)
            return


        if is_blank(line):
            # Blank lines separate blocks
            self._flush_buffer()
            return

        # Non-boundary content
        if self.buffer_type is None:
            # If we’re not inside any block yet, default to ACTION
            self._start_action_block()

        # Parenthetical handling: attach to dialogue if currently in dialogue
        if self.buffer_type == "DIALOGUE" and is_parenthetical(line):
            # TODO: decide whether to store parentheticals separately; v1 appends
            self.buffer_lines.append(line.strip())
            return

        self.buffer_lines.append(line.strip())

    def _start_new_scene(self, heading_line: str) -> None:
        self.scene_index += 1
        self.scene_heading = heading_line.strip()
        self.stats.scenes = self.scene_index + 1

        # Reset per-scene block index
        self.block_index = 0

    def _start_dialogue_block(self, speaker: str) -> None:
        # Ensure we have a scene (some scripts may begin without a heading)
        if self.scene_index < 0:
            self._start_new_scene("NO_SCENE_HEADING")

        self.buffer_type = "DIALOGUE"
        self.buffer_character = speaker
        self.buffer_lines = []

    def _start_action_block(self) -> None:
        if self.scene_index < 0:
            self._start_new_scene("NO_SCENE_HEADING")

        self.buffer_type = "ACTION"
        self.buffer_character = None
        self.buffer_lines = []

    def _flush_buffer(self) -> None:
        if not self.buffer_type or not self.buffer_lines:
            # Reset buffer cleanly
            self.buffer_type = None
            self.buffer_character = None
            self.buffer_lines = []
            return

        text = " ".join([ln for ln in self.buffer_lines if ln])
        wc = count_words(text)

        block = Block(
            script_id=self.script_id,
            scene_index=self.scene_index,
            scene_heading=self.scene_heading,
            block_index=self.block_index,
            block_type=self.buffer_type,
            character=self.buffer_character if self.buffer_type == "DIALOGUE" else None,
            text=text,
            word_count=wc,
        )
        self.blocks.append(block)

        # Update stats / indices
        self.stats.blocks += 1
        if self.buffer_type == "DIALOGUE":
            self.stats.dialogue_blocks += 1
        else:
            self.stats.action_blocks += 1

        self.block_index += 1

        # Reset buffer
        self.buffer_type = None
        self.buffer_character = None
        self.buffer_lines = []

    def _finalize_stats(self) -> None:
        # Nothing special yet; placeholder for future stats checks
        pass


def parse_script(cleaned_text: str, script_id: str) -> Dict[str, Any]:
    """
    Convenience wrapper returning both blocks and stats.
    """
    parser = ScriptParser(script_id=script_id)
    blocks = parser.parse(cleaned_text)
    return {"blocks": blocks, "stats": parser.stats}
