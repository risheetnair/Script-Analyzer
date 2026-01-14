# Normalization Pipeline (v1)

This document describes the preprocessing and normalization steps used to convert raw screenplay text extracted from PDFs into clean, block-preserving text suitable for parsing and analysis.

The goal of normalization is to reduce PDF extraction noise while preserving screenplay structure.

---

## Overview

PDF-to-text extraction introduces:

- hard line breaks every few words
- hyphenation and split-word artifacts
- page numbers and form-feed markers
- inconsistent spacing

Normalization transforms raw text into clean text without attempting to reconstruct perfect screenplay formatting.

---

## Inputs and Outputs

- Input: `data/raw/<script>.txt`
- Output: `data/clean/<script>_clean.txt`

No parsing or classification occurs at this stage.

---

## Step 0 — Line Canonicalization

For each line:

- Convert Windows line endings to Unix (`\r\n` → `\n`)
- Strip trailing whitespace
- Preserve leading whitespace
- Leave most internal spacing untouched until later steps

Purpose: Ensure predictable behavior in later rules.

---

## Step 1 — Remove PDF Artifacts

Drop lines that match:

- form-feed markers (e.g., lines containing `\f`)
- standalone page numbers (lines containing only digits)
- obvious repeated headers or footers (if present)

These lines do not represent screenplay content.

---

## Step 2 — Identify Hard Boundaries

Hard boundaries define where text should **not** be merged across.

Hard boundaries include:

- blank lines
- scene headings (`INT.`, `EXT.`, `INT./EXT.`, `I/E`)
- character cues (short, mostly uppercase lines)
- transitions ending with `TO:` (e.g., `CUT TO:`)

These boundaries preserve screenplay structure.

---

## Step 3 — Repair Split Words (Conservative)

PDF extraction can split words into fragments such as:

- `sl ept`
- `Decla re`

Conservative repair rules:

- merge only alphabetic fragments
- merge only when fragments appear mid-word
- avoid merging across block boundaries

The goal is to fix obvious extraction artifacts without altering legitimate spacing.

---

## Step 4 — Unwrap Wrapped Lines Within Blocks

Within blocks of text between hard boundaries:

- merge consecutive non-boundary lines into a single paragraph
- insert a single space between merged lines
- if a line ends with a hyphen (`-`), merge without adding a space

This step restores logical paragraphs for dialogue and action.

---

## Step 5 — Character Cue Modifiers (Optional)

Character cues may include modifiers:

- `FLETCHER (PRE-LAP)`
- `JIM (O.S.)`

In v1:

- the full cue line is preserved in the cleaned text
- modifiers are stripped later during parsing for character aggregation

---

## Output Guarantees

After normalization:

- scene headings remain on standalone lines
- character cues remain on standalone lines
- dialogue and action blocks are unwrapped into coherent paragraphs
- PDF artifacts are removed

The cleaned text is intentionally simple and predictable for downstream parsing.

---

## Out of Scope (v1)

- montage segmentation
- shot-level directives
- sound design semantics
- perfect reconstruction of screenplay formatting

These may be explored in later iterations.

---

Run this to not split the words:
python3 -m scripts.normalize_all --no-split-repair
