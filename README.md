# ComfyUI-HR-Endless-Sampler-Manual

A fork of [hradec/ComfyUI-HR-Endless-Sampler](https://github.com/hradec/ComfyUI-HR-Endless-Sampler)
that adds an optional manual replacement for the Gemma 4 director, so the
chunked sampler can run with no local LLM at all.

Everything upstream does is unchanged and still available. This fork only
adds a way to bypass one part of it.

---

## Why

`HR Endless Sampler` normally runs Gemma 4 12B through `llama-cpp-python`
to plan shot timing and rewrite the `detailed_description` field for every
chunk. That is the feature that makes the upstream node good, and if it
works on your machine you should use it.

It does not work everywhere:

- `llama-cpp-python` ships prebuilt wheels compiled for specific CPU
  instruction sets. A wheel built with AVX-512 crashes with
  `STATUS_ILLEGAL_INSTRUCTION` (`0xc000001d`) on Intel consumer chips
  where AVX-512 is fused off, such as 12th–14th gen Core.
- The CUDA wheels need a CUDA runtime whose major version matches the
  build. A mismatch fails at DLL load with
  "Could not find module ... llama.dll (or one of its dependencies)".
- On CPU, a 12B model adds roughly a minute per director call, once for
  planning plus once per chunk.

If you already generate your prompts elsewhere — another model, a script,
or by hand — the director is work you have done twice.

## What this fork adds

**`chunk_descriptions`** — a new optional multiline input on
`HREndlessSampler`. Leave it empty and nothing changes. Fill it in and:

- Gemma 4 is never constructed and `llama_cpp` is never imported, even
  when the prompt still contains `[Shot N]` markers.
- Each block replaces the `detailed_description` field for one chunk,
  through the same `_prompt_with_gemma_description` path the director's
  own output uses. Continuation labels and picture-anchor handling are
  applied identically.
- Everything else in the base prompt — `subject_definitions`, `summary`,
  `retention_analysis`, `overall_soundscape`, `non_diegetic_music` — is
  preserved by the upstream code as normal.

**`chunk_description_log`** — a new STRING output reporting what the node
did with the blocks: how many were supplied, how many chunks were planned,
and which blocks went unused.

### Format

Blocks are separated by a line containing three or more dashes. Lines
whose first non-space character is `#` are ignored, so a generator can
emit a configuration header without it being read as chunk 1.

```
# chunk_frames = 141
# fps = 24
# video_continuation = 22
# total duration (seconds) = 12.250
# total duration (frames) = 294
# chunks = 3
[Shot 1] She pushes through the morgue doors and crosses to the table.
In a continuous movement, the camera tracks her from the left.
---
The track continues as she reaches the table and draws back the sheet.
---
She leans in as the overhead lamp throws her face into hard relief.
```

### Block count rules

| Blocks supplied | Behaviour |
|---|---|
| 0 | Unchanged; the upstream planner and Gemma run as normal. |
| 1 | Reused for every chunk. |
| exactly the chunk count | One block per chunk, in order. |
| fewer than the chunk count | `ValueError` before anything is sampled. |
| more than the chunk count | Runs; unused blocks reported in the log. |

The too-few case is checked up front, immediately after the chunk plan is
built, so it fails in under a second instead of after earlier chunks have
already spent minutes sampling.

### Finding the chunk count

Run once with `chunk_descriptions` empty and read `Preparing N chunks` from
the console, or compute it:

```
new frames per chunk = chunk_frames - video_continuation
chunk_count = 1                                   if total_frames <= chunk_frames
              1 + ceil((total_frames - chunk_frames) / new_frames_per_chunk)
```

## Writing the blocks with an LLM

`docs/chunk_descriptions_prompt_block.md` is a self-contained instruction
block for generating `chunk_descriptions` with any capable model, local or
hosted. It encodes the rules the upstream Gemma director works to, taken
from the project's own `gemma4_prompts.txt`: local per-chunk timelines,
continuation from carried frames, concurrency defaults, `[Shot N]` marker
semantics, the `In a continuous movement,` requirement for unmarked camera
moves, `Name (<Subject N>)` conventions, and verbatim dialogue repeated
across every overlapping slice.

It is written for `chunk_frames = 141`, `fps = 24`,
`video_continuation = 22`, and contains an "Adapting this block" section
with the general formulas for any other configuration.

The block also emits a `#` comment header recording the settings it
assumed, which the sampler ignores when parsing. That makes a generated
file self-describing, and lets you check the `# chunks =` value against
`chunk_description_log` to catch a mismatch before rendering.

## What you give up

The director sees the rendered stills from the previous chunk and treats
them as authoritative over the plan. Writing blocks in advance means
working from intent rather than from what the model actually produced, so
if a chunk drifts, later blocks will not know. You also compute local shot
timestamps yourself instead of receiving them as
`required_local_markers`.

For a scripted shot list this is usually fine. For long, loosely specified
sequences the upstream director is better.

## Install

Replace `custom_nodes/ComfyUI-HR-Endless-Sampler/` with this fork, or apply
`manual-chunk-descriptions.patch` to a clean upstream checkout:

```
git apply manual-chunk-descriptions.patch
```

Restart ComfyUI. Existing workflows keep working; the new input defaults to
empty. Because the node gained an output, you may need to re-add it in a
saved workflow for `chunk_description_log` to appear.

## Changes from upstream

All changes are confined to `nodes.py`:

- `MANUAL_CHUNK_SEPARATOR`, `_parse_manual_chunk_descriptions`,
  `_manual_description_for_chunk`, `_validate_manual_chunk_descriptions`
- `chunk_descriptions` input and `chunk_description_log` output on the
  `HREndlessSampler` schema
- `gemma_director_needed` additionally requires no manual blocks
- a branch in the chunk loop that uses a manual block when present

## Licence

Apache License 2.0, inherited from upstream. Modified files carry a notice
of change as required by section 4(b). Upstream copyright and the original
`LICENSE` and `NOTICE` are retained unchanged.
