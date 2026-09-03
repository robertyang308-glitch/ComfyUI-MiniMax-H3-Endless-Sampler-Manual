"""
_check_chunk_headers.py

Scans the current folder and all subfolders for .txt prompt files, reads the
`#` headers, and checks that the chunk layout adds up. Files with no headers
at all are ignored. Nothing is deleted without an explicit typed
confirmation.

Checks performed on each file that has a chunk_frames header:

  1. every span is on the model's frame grid
  2. every overlap is on the grid and strictly smaller than its own span
  3. the chunk_frames and context_keyframes lists are the same length
  4. `# chunks = N` matches the number of spans, when present
  5. delivered frames reach the declared total:
        span_1 + sum(span_i - effective_overlap_i)  >=  total frames

     where effective_overlap is max(overlap, 5). Even with
     `context_keyframes = 0` the sampler keeps a five-frame packing prefix
     on every chunk after the first and trims it from the output, so a
     declared overlap of 0 still costs five frames per chunk.

Run from the folder you want to scan:
    python _check_chunk_headers.py
"""

import os
import re
import sys

# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

FRAME_MATH = "h3"        # "h3" (17k+5), "ltx" (8k+1), "wan" (4k+1), "none"
DEFAULT_FPS = 24.0
EXTENSIONS = (".txt",)
QUARANTINE = "_failed_headers"


def on_grid(value, mode=FRAME_MATH):
    if mode == "h3":
        return value >= 5 and (value - 5) % 17 == 0
    if mode == "ltx":
        return value >= 1 and (value - 1) % 8 == 0
    if mode == "wan":
        return value >= 1 and (value - 1) % 4 == 0
    return True


def nearest_below(value, mode=FRAME_MATH):
    if mode == "h3":
        return max(5, value - (value - 5) % 17)
    if mode == "ltx":
        return max(1, value - (value - 1) % 8)
    if mode == "wan":
        return max(1, value - (value - 1) % 4)
    return value


# --------------------------------------------------------------------------
# header parsing
# --------------------------------------------------------------------------

# Even at context_keyframes = 0 the sampler keeps a five-frame packing
# prefix on chunks after the first, and trims it from the output.
MIN_TRIM = 5

NUMBER = r"[-+]?\d*\.?\d+"


def header_numbers(text, key):
    """Return a list of ints for `# key = a, b, c`, or None when absent."""
    pattern = re.compile(
        r"(?im)^[ \t]*#[ \t]*" + re.escape(key) + r"[ \t]*[=:][ \t]*([0-9,\s]+)$")
    match = pattern.search(text)
    if match is None:
        return None
    parts = [p.strip() for p in match.group(1).split(",") if p.strip()]
    try:
        return [int(p) for p in parts] or None
    except ValueError:
        return None


def header_number(text, key):
    """Return a single float for `# key = value`, or None when absent."""
    pattern = re.compile(
        r"(?im)^[ \t]*#[ \t]*" + re.escape(key) + r"[ \t]*[=:][ \t]*(" + NUMBER + r")")
    match = pattern.search(text)
    return float(match.group(1)) if match else None


def total_frames_of(text, fps):
    for key in ("total duration (frames)", "total_duration_frames", "frames"):
        value = header_number(text, key)
        if value is not None:
            return int(round(value)), f"# {key}"
    for key in ("total duration (seconds)", "total_duration_seconds",
                "seconds", "duration"):
        value = header_number(text, key)
        if value is not None:
            return int(round(value * fps)), f"# {key}"
    return None, None


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def check(text, fps=DEFAULT_FPS):
    """Return (status, list_of_messages). status is 'ok', 'fail' or 'skip'."""
    spans = header_numbers(text, "chunk_frames")
    overlaps = header_numbers(text, "context_keyframes")
    total, total_key = total_frames_of(text, fps)
    declared = header_numbers(text, "chunks")

    if spans is None and overlaps is None and total is None:
        return "skip", ["no headers"]
    if spans is None:
        return "skip", ["no `# chunk_frames` header; nothing to check"]

    problems = []

    for position, span in enumerate(spans, 1):
        if not on_grid(span):
            problems.append(
                f"span {position} is {span}, off the grid "
                f"(nearest valid at or below: {nearest_below(span)})")

    if overlaps is None:
        overlaps = [5] * len(spans)
        note = "no `# context_keyframes`; assuming 5 for every chunk"
    else:
        note = None
        if len(overlaps) == 1:
            overlaps = overlaps * len(spans)
        elif len(overlaps) != len(spans):
            problems.append(
                f"context_keyframes has {len(overlaps)} entries but "
                f"chunk_frames has {len(spans)}")
            overlaps = (overlaps + [5] * len(spans))[:len(spans)]

    for position in range(1, len(spans)):
        overlap = overlaps[position]
        if overlap and not on_grid(overlap):
            problems.append(f"overlap {position + 1} is {overlap}, off the grid")
        if overlap >= spans[position]:
            problems.append(
                f"overlap {position + 1} is {overlap}, not smaller than its "
                f"span of {spans[position]}")

    if declared and declared[0] != len(spans):
        problems.append(
            f"`# chunks = {declared[0]}` but chunk_frames lists {len(spans)} spans")

    effective = [max(value, MIN_TRIM) for value in overlaps]
    delivered = spans[0] + sum(
        span - effective[index] for index, span in enumerate(spans) if index)
    if any(value < MIN_TRIM for value in overlaps[1:]):
        note = (note + "; " if note else "") + (
            f"overlaps below {MIN_TRIM} counted as {MIN_TRIM} (packing prefix)")

    if total is None:
        problems.append("no total duration header, so coverage cannot be checked")
    elif delivered < total:
        problems.append(
            f"delivers {delivered} frames but {total_key} declares {total}; "
            f"short by {total - delivered}")

    summary = (f"{len(spans)} chunks, delivers {delivered} frames"
               + (f", total {total}" if total is not None else ""))
    messages = [summary] + ([note] if note else []) + problems
    return ("fail" if problems else "ok"), messages


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    root = os.getcwd()
    print(f"Scanning {root}")
    print(f"Frame math: {FRAME_MATH}, fps {DEFAULT_FPS:g}\n")

    results = {"ok": [], "fail": [], "skip": []}
    for folder, _dirs, names in os.walk(root):
        if os.path.basename(folder) == QUARANTINE:
            continue
        for name in sorted(names):
            if not name.lower().endswith(EXTENSIONS):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
                    text = handle.read()
            except OSError as error:
                print(f"[skip] {path}: {error}")
                continue
            status, messages = check(text)
            results[status].append((path, messages))

    for path, messages in results["fail"]:
        print(f"FAIL  {os.path.relpath(path, root)}")
        for message in messages:
            print(f"        {message}")

    print(f"\n{len(results['ok'])} ok, {len(results['fail'])} failed, "
          f"{len(results['skip'])} skipped (no headers)")

    if not results["fail"]:
        return

    print("\nWhat would you like to do with the failing files?")
    print("  [m] move them to a " + QUARANTINE + " folder  (recommended)")
    print("  [d] delete them permanently")
    print("  [n] nothing                                    (default)")
    choice = input("Choice [m/d/N]: ").strip().lower()

    if choice == "d":
        typed = input(f"Type DELETE to permanently remove {len(results['fail'])} "
                      f"file(s): ").strip()
        if typed != "DELETE":
            print("Not confirmed. Nothing was changed.")
            return
        for path, _messages in results["fail"]:
            try:
                os.remove(path)
                print(f"deleted {path}")
            except OSError as error:
                print(f"could not delete {path}: {error}")

    elif choice == "m":
        target = os.path.join(root, QUARANTINE)
        os.makedirs(target, exist_ok=True)
        for path, _messages in results["fail"]:
            destination = os.path.join(target, os.path.basename(path))
            suffix = 1
            while os.path.exists(destination):
                stem, extension = os.path.splitext(os.path.basename(path))
                destination = os.path.join(target, f"{stem}_{suffix}{extension}")
                suffix += 1
            try:
                os.replace(path, destination)
                print(f"moved {os.path.relpath(path, root)} -> "
                      f"{os.path.relpath(destination, root)}")
            except OSError as error:
                print(f"could not move {path}: {error}")

    else:
        print("Nothing was changed.")


if __name__ == "__main__":
    main()
