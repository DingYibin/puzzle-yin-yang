"""Benchmark solver on example puzzles (10 runs each, average time)."""
import json
import time
import sys
from pathlib import Path

from yinyang_solver import Solver, decode

EXAMPLES = sorted(Path("examples").glob("*.json"))
RUNS = 10
TIMEOUT = 30.0

results = {}
for path in EXAMPLES:
    data = json.loads(path.read_text())
    task = data["task"]
    N = data["puzzleWidth"]
    grid = decode(task, N)
    label = f"{path.stem} ({N}x{N}, {data.get('puzzleSize','?')})"

    times = []
    for i in range(RUNS):
        s = Solver(time_limit=TIMEOUT, verbose=False)
        s.load([row[:] for row in grid])
        t0 = time.perf_counter()
        ok = s.solve()
        t = time.perf_counter() - t0
        times.append(t)

    avg = sum(times) / len(times)
    best = min(times)
    results[label] = {"avg": avg, "best": best, "ok": ok}
    print(f"{label:45s}  avg={avg*1000:8.3f}ms  best={best*1000:8.3f}ms  ok={ok}")

print()
print("Summary:")
for label, r in results.items():
    print(f"  {label:45s}  {r['avg']*1000:8.3f}ms  ok={r['ok']}")
