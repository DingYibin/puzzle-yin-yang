"""Fetch 100 unique solvable puzzles per size/difficulty via random fetch.

Saved individually to puzzles/{size_key}/{n:03d}.json, then merged to
puzzles_all.json after all sizes are complete.
"""
import json
import os
import random
import re
import time
from pathlib import Path

import requests

from yinyang_solver import Solver, decode, encode

SIZE_MAP = {
    '6e': '0', '6n': '1', '6h': '2',
    '10e': '3', '10n': '4', '10h': '5',
    '15e': '6', '15n': '7', '15h': '8',
    '20e': '9', '20n': '10', '20h': '11',
    '25e': '12', '25n': '13', '25h': '14',
}

SIZE_LABELS = {
    '6e': '6×6 easy',     '6n': '6×6 normal',     '6h': '6×6 hard',
    '10e': '10×10 easy',  '10n': '10×10 normal',  '10h': '10×10 hard',
    '15e': '15×15 easy',  '15n': '15×15 normal',  '15h': '15×15 hard',
    '20e': '20×20 easy',  '20n': '20×20 normal',  '20h': '20×20 hard',
    '25e': '25×25 easy',  '25n': '25×25 normal',  '25h': '25×25 hard',
}

TARGET = 100
HTTP_TIMEOUT = 30
DELAY_MEAN = 0.5
DELAY_STD = 0.3
PUZZLE_DIR = Path("puzzles")


def is_task_valid(task: str) -> bool:
    """Check task RLE encoding is canonical: consecutive lowercase letters
    must be 'z' repeated except possibly the last character."""
    i = 0
    n = len(task)
    while i < n:
        if task[i].islower():
            j = i
            while j < n and task[j].islower():
                j += 1
            if j - i > 1:
                for k in range(i, j - 1):
                    if task[k] != 'z':
                        return False
            i = j
        else:
            i += 1
    return True


def _rand_delay():
    d = random.gauss(DELAY_MEAN, DELAY_STD)
    d = max(0.1, min(3.0, d))
    time.sleep(d)


def fetch_random(size_param: str) -> tuple:
    """Fetch a random puzzle via GET, return (task, w, h, pid, date) or (None,)*5."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    url = f"https://cn.puzzle-yin-yang.com/?size={size_param}"
    for _ in range(9):
        try:
            r = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            html = r.text
            task_m = re.search(r"var\s+task\s*=\s*'([^']+)'", html)
            w_m = re.search(r'puzzleWidth\s*:\s*(\d+)', html)
            h_m = re.search(r'puzzleHeight\s*:\s*(\d+)', html)
            pid_m = re.search(r'id="puzzleID"\s*>\s*([0-9,]+)', html)
            if task_m and w_m:
                task = task_m.group(1)
                w = int(w_m.group(1))
                h = int(h_m.group(1)) if h_m else w
                if is_task_valid(task):
                    pid = pid_m.group(1) if pid_m else None
                    return task, w, h, pid, None
        except Exception:
            pass
        _rand_delay()
    return None, 0, 0, None, None


def save_one(size_key: str, idx: int, data: dict):
    """Save single puzzle to puzzles/{size_key}/{idx:03d}.json."""
    d = PUZZLE_DIR / size_key
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{idx:03d}.json", "w") as f:
        json.dump(data, f, ensure_ascii=False)


def merge_all():
    """Read all puzzles/*/ and merge into puzzles_all.json."""
    sizes_out = {}
    total = 0
    for size_key in sorted(SIZE_MAP, key=lambda k: (int(k.rstrip('ehn')),
                                                    {'e': 0, 'n': 1, 'h': 2}.get(k[-1] if k[-1] in 'ehn' else 'n', 1))):
        d = PUZZLE_DIR / size_key
        puzzles = []
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.suffix == ".json":
                    with open(f) as fh:
                        puzzles.append(json.load(fh))
        N = int(size_key.rstrip('ehn'))
        diff = size_key[-1] if size_key[-1] in 'ehn' else ''
        label = f"{N}×{N} {diff}" if diff else f"{N}×{N}"
        sizes_out[size_key] = {"size": label, "sizeParam": SIZE_MAP[size_key], "puzzles": puzzles}
        total += len(puzzles)
    out = {"generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"), "sizes": sizes_out}
    with open("puzzles_all.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nMerged {total} puzzles into puzzles_all.json")


def main():
    total_sizes = len(SIZE_MAP)
    for si, size_key in enumerate(sorted(SIZE_MAP, key=lambda k: (int(k.rstrip('ehn')),
                                                                  {'e': 0, 'n': 1, 'h': 2}.get(k[-1] if k[-1] in 'ehn' else 'n', 1))), 1):
        size_param = SIZE_MAP[size_key]
        label = SIZE_LABELS[size_key]
        N = int(size_key.rstrip('ehn'))

        target_dir = PUZZLE_DIR / size_key
        target_dir.mkdir(parents=True, exist_ok=True)

        # Load existing
        seen = set()
        existing_count = 0
        for f in sorted(target_dir.iterdir()):
            if f.suffix == ".json":
                with open(f) as fh:
                    data = json.load(fh)
                seen.add(data["task"])
                existing_count += 1

        needed = TARGET - len(seen)
        print(f"\n── [{si}/{total_sizes}] {label} — {existing_count} exist, {needed} needed ──")

        attempts = 0
        while len(seen) < TARGET:
            attempts += 1
            task, w, h, pid, _ = fetch_random(size_param)
            if not task:
                continue

            if task in seen:
                print(f"  [{attempts:4d}] dup, skip")
                _rand_delay()
                continue

            # Decode and solve
            grid = decode(task, w)
            solver = Solver(time_limit=30.0, debug=False)
            solver.load(grid)
            t0 = time.perf_counter()
            ok = solver.solve()
            t = time.perf_counter() - t0

            if not ok:
                print(f"  [{attempts:4d}] unsolvable, skip")
                _rand_delay()
                continue

            seen.add(task)
            idx = existing_count + len(seen) - 1
            data = {"id": idx, "task": task, "width": w, "height": h, "puzzleID": pid or str(idx)}
            save_one(size_key, idx, data)

            t_str = f"{t*1e6:.0f}μs" if t < 0.001 else f"{t*1000:.2f}ms" if t < 1.0 else f"{t:.3f}s"
            print(f"  [{attempts:4d}] ✓ #{idx:3d}  {t_str:>8s}  task={task[:30]}…")
            _rand_delay()

        print(f"  → Done: {len(seen)}/{TARGET} in {attempts} attempts")

    print(f"\n{'='*60}")
    merge_all()
    print("Done.")


if __name__ == "__main__":
    main()
