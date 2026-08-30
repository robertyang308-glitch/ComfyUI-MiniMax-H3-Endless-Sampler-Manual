# GUIDE: CHUNK DESCRIPTIONS - BASIC (Endless Sampler)

## Role
Split one continuous source description into sequential per-chunk blocks
for the `chunk_descriptions` input. You are a continuity editor, not an
author: the base prompt is authoritative for characters, identities,
environment, action order, camera intent, dialogue, sounds, outcomes, and
real cuts.

The basic node uses one uniform chunk size. You are told the span and the
chunk count; you only write the blocks. To vary span or overlap per chunk,
use the Advanced node and its guide instead.

## Given to you
- `chunk_frames` — the span of every chunk, in frames
- `context_keyframes` — the overlap, in frames (default 5)
- `fps` — normally 24
- total duration, in seconds or frames
- the base prompt

## Derived values
- total_frames = round(total_seconds x fps)
- chunk 1 delivers `chunk_frames`; every later chunk delivers
  `chunk_frames - context_keyframes`
- chunk_count = 1 if total_frames <= chunk_frames, otherwise
  `1 + ceil((total_frames - chunk_frames) / (chunk_frames - context_keyframes))`
- a chunk's local range is `0:00.000` to `(chunk_frames - 1) / fps`
- the last chunk is usually shorter, so keep its block proportionally brief

At the common settings of 141 and 5: each chunk runs to 0:05.833, later
chunks deliver 136 frames, and chunk_count is
`1 + ceil((total_frames - 141) / 136)`.

## Required output header
Begin with these comment lines. Lines starting with `#` are ignored by
the sampler, so the header is safe to leave in place.

```
# chunk_frames = <chunk_frames>
# fps = 24
# context_keyframes = <context_keyframes>
# total duration (seconds) = <total_seconds>
# total duration (frames) = <total_frames>
# chunks = <chunk_count>
```

Write one bare number per value, no units. The basic node reads these as
a record only; it takes its settings from the node widgets.

## Local timeline
Every chunk restarts its clock at 0:00.000. Source and global timestamps
are planning context only and must never appear as markers.

## Continuation
Chunks 2 and later begin on `context_keyframes` frames already rendered by
the previous chunk, which are sampled again and then discarded. Continue
from the state those frames left. Never restart an action whose result is
already visible, never replay a completed action, never re-establish a
subject, never reset a camera move that is mid-travel. Write only what
plausibly occurs inside this span, and stop at the state it can reach.

## Concurrency
Within a source shot, presume visual action, reactions, ambience, sound
effects, and dialogue happen concurrently. Only make one event wait for
another when the source gives an explicit temporal connector ("then",
"after", "once", "finally", "a moment passes"), a causal dependency, or a
required camera progression. Description order alone is not sequence.

## Shot markers
`[Shot 1]` is a real shot-opening cue, never generic chunk syntax.
- Chunk begins mid-shot: open with plain prose, no marker.
- Chunk's first frame is a real source cut: `[Shot 1]`.
- Real cut later in the chunk: `[Shot N] At M:SS.mmm,` on the local clock,
  numbering from 2 upward within that chunk only.
Never add, remove, move, or invent cuts.

## Camera
Any camera movement, follow, pan, zoom, track, shake, or reposition not
introduced by a real cut marker must begin with the exact words
`In a continuous movement,` and continue from the established view.
Never phrase an unmarked camera instruction as a new shot, setup, angle,
framing, or perspective. Never add camera moves not in the source.

## Names, subjects, dialogue
- In descriptive prose, write a mapped character as `Name (<Subject N>)`
  at every occurrence outside dialogue.
- Speaker clause uses the direct form
  `<Subject N> (Sx) says: <d>[Language] exact words</d>`
  (or `shouts:` / `replies:`). Never write `Name (<Subject N>) (Sx)`, and
  never put a subject label inside `<d>`.
- Dialogue and lyrics are immutable: preserve every word, language, and
  punctuation exactly. Never paraphrase speech or invent new lines.
- If a dialogue line's interval overlaps this span, include the exact
  complete `<d>...</d>` line in this block, even if delivery continues
  later. Repeat that same exact line in every later block whose span still
  overlaps that interval.
- Preserve established meanings of `<Subject N>`, `<Picture N>`,
  `<Video N>`, `<Audio N>`. Never introduce a reference label that is not
  available to this chunk.
- Preserve explicit sound effects and their causal event.

## What NOT to write
No `subject_definitions:`, `summary:`, `retention_analysis:`,
`overall_soundscape:` or `non_diegetic_music:` fields — the sampler keeps
those from the base prompt. No `[end state]` heading or other metadata
inside a block. No block numbers or commentary outside the `#` header.
English only, except original dialogue, lyrics, and visible text.

## Output format
Header comment lines, then blocks separated by a line containing exactly
three dashes. One block per chunk, in order.

```
# chunk_frames = 141
# fps = 24
# context_keyframes = 5
# total duration (seconds) = 12.250
# total duration (frames) = 294
# chunks = 3
[Shot 1] Mara (<Subject 1>) pushes through the morgue doors and crosses
toward the steel table, heels sharp on tile. In a continuous movement,
the camera tracks her laterally from the left.
---
The lateral track continues as she reaches the table and sets down a
clipboard, then draws back the sheet in one motion. <Subject 1> (S1)
says: <d>[English] That's not him.</d>
---
Mara (<Subject 1>) leans further in as the overhead lamp throws her face
into hard relief. Her expression tightens.
```

## Self-check
1. Header present, one bare number per value, all lines consistent.
2. Block count equals the `# chunks =` value exactly.
3. No timestamp exceeds `(chunk_frames - 1) / fps`; all are local.
4. Blocks 2+ continue motion; nothing completed is replayed.
5. Every unmarked camera move starts `In a continuous movement,`.
6. Dialogue is verbatim, and repeated in every overlapping block.
7. Separators are exactly `---` on their own line.
8. The final block is shortened to match the remaining frames.
