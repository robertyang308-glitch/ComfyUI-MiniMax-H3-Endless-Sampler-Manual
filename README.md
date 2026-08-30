# ComfyUI-HR-Endless-Sampler-Manual

A fork of [hradec/ComfyUI-HR-Endless-Sampler](https://github.com/hradec/ComfyUI-HR-Endless-Sampler)
that lets you write the per-chunk description text yourself, choose a
different span for each chunk, and validate the whole layout before
committing to a render.

Upstream behaviour is unchanged when the new inputs are left empty.

---

## Two nodes

**Endless Sampler** — the basic node. Upstream behaviour plus
`chunk_descriptions`, with `chunk_frames` and `context_keyframes` taken
from the widgets as usual.

**Endless Sampler (Advanced)** — adds per-chunk spans and overlaps
declared in the `chunk_descriptions` header, and a `validate_only` dry
run. Start with the basic node; move up when a single uniform chunk size
stops fitting the material.

## What this fork adds

**`chunk_descriptions`** — an optional multiline input on
the sampler. Each block supplies the `detailed_description` for one
chunk. Everything else in the base prompt — `subject_definitions`,
`summary`, `retention_analysis`, `overall_soundscape`,
`non_diegetic_music` — is preserved as normal, so blocks carry description
prose only.

**Per-chunk spans and overlaps** (Advanced node). `# chunk_frames =` and
`# context_keyframes =` header lines inside `chunk_descriptions` override
the widgets. One value sets a uniform setting; a comma list sets each
chunk individually:

```
# chunk_frames = 141,  90,  90, 56
# context_keyframes = 5,  22,   5,  5
```

This turns `chunk_frames` into an upper limit rather than a fixed size.
Put cuts on chunk boundaries by shortening the span that ends there, keep
an unbroken dialogue exchange inside one longer chunk, and raise the
overlap only on boundaries that fall inside continuous motion.

Overlaps must sit on the same 17k+5 grid and be strictly smaller than
their own span. The two lists must be the same length.

**`validate_only`** (Advanced node) — plans and validates, then returns without sampling.
No model is loaded. Reports the chunk table, spans, trims, local end
times, and the block count, so a layout mistake costs a second instead of
an hour.

**Shorter node names.** Display names drop the `HR ` prefix: *Endless
Sampler*, *Endless Sampler (Advanced)*, *Endless Sampler Preview*,
*Endless Sampler Save Video*, *Endless Sampler Load Video*. The underlying
`node_id` values are unchanged, so saved workflows still load.

**`chunk_description_log`** — a new STRING output recording how many
blocks were supplied, how many chunks were planned, and which blocks went
unused.

---

## Prompting: a two-step process

### Step 1 — the base prompt

Write the whole piece as one MiniMax H3 prompt, on the **global**
timeline, with `[Shot N]` markers at your real cuts. This goes in the
sampler's `prompt` widget. It supplies every field except the description
body, and those fields are sent with every chunk.

The text on the upstream conditioning node is not used for sampling; the
sampler re-encodes its own prompt per chunk. That node still supplies the
reference images.

### Step 2 — the chunk descriptions

Derive one description block per chunk from the base prompt, each on its
own **local** timeline starting at 0:00.000, and paste them into
`chunk_descriptions` separated by `---`.

`docs/chunk_descriptions_guide.md` is a complete specification for this
step: span selection, local timelines, continuation from the overlapped
frames, concurrency defaults, `[Shot N]` semantics, the
`In a continuous movement,` requirement for unmarked camera moves,
`Name (<Subject N>)` conventions, and verbatim dialogue repeated across
every overlapping block. It is written to be handed to any writing tool,
or followed by hand.

### Finding the chunk count

Run once with `validate_only` on. The report gives the planned chunks and
their spans. Or compute it: chunk 1 delivers its full span, every later
chunk delivers `span - 5`, and the delivered total must reach
`total_frames`.

For a uniform span and a uniform overlap:

```
chunk_count = 1                                            if total_frames <= span
              1 + ceil((total_frames - span) / (span - overlap))
```

With the default overlap of 5 and a 141-frame span, that is
`1 + ceil((total_frames - 141) / 136)`.

Spans must sit on H3's grid, `(span - 5) % 17 == 0`: 56, 73, 90, 107, 124,
141, 175 and so on.

### Block count rules

| Blocks supplied | Behaviour |
|---|---|
| 0 | Unchanged; the upstream planner runs. |
| 1 | Reused for every chunk. |
| exactly the chunk count | One block per chunk, in order. |
| fewer than the chunk count | `ValueError` before anything is sampled. |
| more than the chunk count | Runs; unused blocks reported in the log. |

The too-few case is checked immediately after the chunk plan is built, so
it fails in under a second rather than after earlier chunks have already
spent minutes sampling.

---

## Overlap and cost

Chunks 2 and later overlap the previous chunk by `context_keyframes`
frames, default 5, or by a per-chunk value on the Advanced node. Those frames are sampled again and then trimmed from
the output, so the earlier chunk's version is the one that survives. Every
chunk costs its full span in sampling time including the overlap, which is
why many small chunks render more slowly than a few large ones.

---

## Install

Replace `custom_nodes/ComfyUI-HR-Endless-Sampler/` with this fork, or apply
`manual-chunk-descriptions.patch` to a clean upstream checkout:

```
git apply manual-chunk-descriptions.patch
```

Restart ComfyUI. Existing workflows keep working; the new inputs default to
empty and off. Because the node gained an output, you may need to re-add it
in a saved workflow for `chunk_description_log` to appear.

## Changes from upstream

All changes are confined to `nodes.py`:

- `_parse_manual_chunk_descriptions`, `_manual_description_for_chunk`,
  `_validate_manual_chunk_descriptions`, `_parse_header_numbers`,
  `_parse_header_chunk_frames`, `_parse_header_context_keyframes`,
  `_chunk_plan_variable`
- `chunk_descriptions` input and `chunk_description_log` output on the
  schema; `validate_only` on the Advanced node only
- `HREndlessSamplerAdvanced`, a subclass setting `ADVANCED = True`
- node display names drop the `HR ` prefix; `node_id` values are unchanged
  so existing workflows keep loading
- plan selection honours `# chunk_frames` and `# context_keyframes`
  header overrides on the Advanced node
- a branch in the chunk loop that uses a manual block when present

`__init__.py` registers the Advanced node alongside the base one.

`_chunk_plan_variable` produces plans identical to the upstream planner
when every span is the same, so the uniform path is unaffected.

## Licence

Apache License 2.0, inherited from upstream. Modified files carry a notice
of change as required by section 4(b). Upstream copyright and the original
`LICENSE` are retained unchanged.
