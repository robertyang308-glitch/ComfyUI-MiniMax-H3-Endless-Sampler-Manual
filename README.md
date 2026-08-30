# ComfyUI-HR-Endless-Sampler-Manual

A fork of [hradec/ComfyUI-HR-Endless-Sampler](https://github.com/hradec/ComfyUI-HR-Endless-Sampler)
that lets you write the per-chunk description text yourself, choose a
different span for each chunk, and validate the whole layout before
committing to a render.

Upstream behaviour is unchanged when the new inputs are left empty.

---

## The two sampler nodes

### Endless Sampler

The basic node. Behaves as upstream does, with one addition:
`chunk_descriptions`, where you supply the `detailed_description` text for
each chunk yourself.

Chunk layout is uniform and comes from the node widgets. `chunk_frames`
sets the span of every chunk; `context_keyframes` sets how many frames
each chunk re-samples from the previous one before trimming them. The
planner divides the latent into equal chunks and you write one block per
chunk, in order.

Use it when the material is even — a single continuous scene, a steady
camera, no hard cuts — or when you are starting out and want one number to
reason about instead of a list.

**Inputs added:** `chunk_descriptions`
**Outputs added:** `chunk_description_log`
**Headers in `chunk_descriptions`:** ignored, treated as comments

### Endless Sampler (Advanced)

Everything the basic node does, plus control of the chunk layout itself
and a way to check that layout before spending render time on it.

**Per-chunk spans.** `chunk_frames` becomes an upper limit rather than a
fixed size. A `# chunk_frames =` header line inside `chunk_descriptions`
can give every chunk its own span, so a boundary can be placed exactly on
a cut instead of wherever an even division happens to fall.

**Per-chunk overlaps.** `# context_keyframes =` does the same for the
overlap. Raise it where a boundary sits inside continuous motion or a
spoken line and the next chunk needs more context to continue from; drop
it to 5 or 0 at a real cut, where there is no motion to carry across and
a large overlap only wastes sampling time.

```
# chunk_frames      = 141, 90, 90, 56
# context_keyframes =   5, 22,  5,  5
```

Both lists must have exactly one entry per chunk and the same length as
each other. Spans and overlaps must sit on H3's grid,
`(value - 5) % 17 == 0`, and every overlap must be strictly smaller than
its own span. A mismatch raises with the offending entry number.

**`validate_only`.** Plans and validates, then returns without sampling
and without loading a model for it. Reports the chunk table, spans,
overlaps, trims, local end times, and the block count. A layout mistake
costs a second instead of an hour.

Use it when the material varies — cuts to land on, dialogue not to split,
long static stretches that could take bigger chunks than the busy parts.

**Inputs added:** `chunk_descriptions`, `validate_only`
**Outputs added:** `chunk_description_log`
**Headers in `chunk_descriptions`:** `# chunk_frames` and
`# context_keyframes` override the widgets

### Which to use

Start with the basic node. Move to Advanced when you find yourself
choosing a chunk size that suits one part of a piece and hurts another, or
when a cut keeps landing in the middle of a chunk.

Both nodes read the same `chunk_descriptions` format, so a set of blocks
written for one works in the other. Only the header lines change meaning.

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

Two specifications are provided, one per node:

- `docs/chunk_descriptions_guide_basic.md` — uniform chunks. You are told
  the span and the chunk count; you write the blocks.
- `docs/chunk_descriptions_guide_advanced.md` — you are told only
  `max_chunk_frames`, and you design the layout: how many chunks, what
  span each uses, and how much each overlaps, before writing the blocks.

Both cover local timelines, continuation from the overlapped frames,
concurrency defaults, `[Shot N]` semantics, the `In a continuous
movement,` requirement for unmarked camera moves, `Name (<Subject N>)`
conventions, and verbatim dialogue repeated across every overlapping
block. Either can be handed to a writing tool or followed by hand.

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
