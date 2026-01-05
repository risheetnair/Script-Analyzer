## Parsing Assumptions (v1)

Screenplays are treated as semi-structured text and parsed using heuristic-based rules.

### Supported

- Scene boundaries detected via `INT.` / `EXT.` headings
- Character cues detected via short uppercase lines (e.g., `DAVID`, `FLETCHER`)
- Dialogue blocks grouped under character cues
- Parentheticals attached to dialogue blocks
- Action and description treated as non-dialogue text

### Intentionally Ignored (v1)

- Page numbers and scene numbering artifacts
- Editorial constructs (montages, shot descriptions)
- Sound design semantics (`O.S.`, `PRE-LAP`, etc.)
- Formatting inconsistencies introduced during PDF extraction

---

## Preprocessing Strategy

PDF-to-text extraction introduces hard line breaks, hyphenation artifacts, and layout noise.

To address this, the preprocessing pipeline:

- Removes page markers and PDF artifacts
- Unwraps hard line breaks within dialogue and action blocks
- Normalizes split words caused by extraction errors
- Preserves logical block boundaries (scene headings, character cues)
