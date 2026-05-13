"""Benchmark solver on example puzzles (10 runs each, average time + trace stats)."""
import json
import time
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
    traces = []
    stacks = []
    nodes_list = []
    for i in range(RUNS):
        s = Solver(time_limit=TIMEOUT, debug=False)
        s.load([row[:] for row in grid])
        t0 = time.perf_counter()
        ok = s.solve()
        t = time.perf_counter() - t0
        times.append(t)
        traces.append(len(s._trace))
        stacks.append(len(s._stack))
        nodes_list.append(s.nodes)

    avg_t = sum(times) / len(times)
    best_t = min(times)
    max_trace = max(traces)
    max_nodes = max(nodes_list)
    results[label] = {"avg_ms": avg_t * 1000, "best_ms": best_t * 1000,
                      "trace": max_trace, "stack": stacks[0], "nodes": max_nodes, "ok": ok}
    print(f"{label:45s}  avg={avg_t*1000:8.3f}ms  best={best_t*1000:8.3f}ms  "
          f"trace={max_trace:6d}  stack={stacks[0]:4d}  nodes={max_nodes:4d}  ok={ok}")

print()
print("Summary:")
print(f"{'':45s}  {'avg':>8}  {'best':>8}  {'trace':>6}  {'stack':>4}  {'nodes':>4}  ok")
for label, r in results.items():
    print(f"  {label:45s}  {r['avg_ms']:8.3f}  {r['best_ms']:8.3f}  "
          f"{r['trace']:6d}  {r['stack']:4d}  {r['nodes']:4d}  {r['ok']}")
