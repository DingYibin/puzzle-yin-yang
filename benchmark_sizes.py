"""Benchmark solver across sizes/difficulties, reading puzzles from puzzles_all.json."""
import json
import time

from yinyang_solver import Solver, decode

SIZE_LABELS = {
    '6e': '6×6 easy',   '6n': '6×6 normal',   '6h': '6×6 hard',
    '10e': '10×10 easy', '10n': '10×10 normal', '10h': '10×10 hard',
    '15e': '15×15 easy', '15n': '15×15 normal', '15h': '15×15 hard',
    '20e': '20×20 easy', '20n': '20×20 normal', '20h': '20×20 hard',
    '25e': '25×25 easy', '25n': '25×25 normal', '25h': '25×25 hard',
}

TIMEOUT = 60.0


def main():
    with open("puzzles_all.json") as f:
        data = json.load(f)

    all_sizes = data["sizes"]
    results = {}

    # Sort by size then difficulty
    size_keys = sorted(all_sizes.keys(),
                       key=lambda k: (int(k.rstrip('ehn')),
                                      {'e': 0, 'n': 1, 'h': 2}.get(k[-1] if k[-1] in 'ehn' else 'n', 1)))

    for size_key in size_keys:
        size_data = all_sizes[size_key]
        label = SIZE_LABELS[size_key]
        puzzles = size_data["puzzles"]
        N = int(size_key.rstrip('ehn'))

        times = []
        traces = []
        stacks = []
        nodes_list = []
        solved = 0
        failed = 0

        print(f"\n{'='*60}")
        print(f"{label} ({len(puzzles)} puzzles)")
        print(f"{'='*60}")

        for p in puzzles:
            pid = p["id"]
            task = p["task"]
            grid = decode(task, N)

            s = Solver(time_limit=TIMEOUT, debug=False)
            s.load(grid)
            t0 = time.perf_counter()
            ok = s.solve()
            t = time.perf_counter() - t0

            if ok:
                solved += 1
                times.append(t)
                traces.append(len(s._trace))
                stacks.append(len(s._stack))
                nodes_list.append(s.nodes)
                t_str = f"{t*1e6:.0f}μs" if t < 0.001 else f"{t*1000:.2f}ms" if t < 1.0 else f"{t:.3f}s"
                print(f"  ID {pid:3d}: {t_str:>10s}  trace={len(s._trace):5d}  stack={len(s._stack):4d}  nodes={s.nodes:3d}")
            else:
                failed += 1
                print(f"  ID {pid:3d}: FAILED")

        avg_t = (sum(times) / len(times)) if times else 0
        best_t = min(times) if times else 0
        avg_trace = (sum(traces) / len(traces)) if traces else 0
        dfs_count = sum(1 for n in nodes_list if n > 0)
        results[size_key] = {
            "label": label,
            "N": N,
            "solved": solved,
            "failed": failed,
            "total": len(puzzles),
            "avg_ms": avg_t * 1000,
            "best_ms": best_t * 1000,
            "avg_trace": avg_trace,
            "max_trace": max(traces) if traces else 0,
            "max_nodes": max(nodes_list) if nodes_list else 0,
            "dfs_count": dfs_count,
        }

    print(f"\n\n{'='*85}")
    print("SUMMARY")
    print(f"{'='*85}")
    print(f"{'Size':14s} {'Puzzles':>7s} {'Solved':>6s} {'Failed':>6s} {'Avg':>10s} {'Best':>10s} {'AvgTr':>8s} {'MaxTr':>8s} {'Nodes':>6s}")
    print(f"{'─'*14} {'─'*7} {'─'*6} {'─'*6} {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*6}")
    for size_key in size_keys:
        r = results[size_key]
        if r['solved'] > 0:
            print(f"{r['label']:14s} {r['total']:7d} {r['solved']:6d} {r['failed']:6d} "
                  f"{r['avg_ms']:9.2f}ms {r['best_ms']:9.2f}ms {r['avg_trace']:7.0f}  {r['max_trace']:8d} {r['max_nodes']:6d}")
        else:
            print(f"{r['label']:14s} {r['total']:7d} {r['solved']:6d} {r['failed']:6d} "
                  f"{'─':>10s} {'─':>10s} {'─':>8s} {'─':>8s} {'─':>6s}")

    # Print table for README
    print(f"\n\nREADME TABLE:")
    print(f"{'| 尺寸 | 难度 | 谜题数 | 平均耗时 | 平均 trace | 最大 trace | 需 DFS |':-^70s}")
    print(f"{'|------|------|--------|---------|-----------|-----------|--------|':-^70s}")
    for size_key in size_keys:
        r = results[size_key]
        size_part = f"{r['N']}×{r['N']}"
        diff_part = size_key[-1] if size_key[-1] in 'ehn' else ''
        if r['solved'] > 0:
            print(f"| {size_part} | {diff_part:6s} | {r['total']:6d} | {r['avg_ms']:7.2f}ms | {r['avg_trace']:9.0f} | {r['max_trace']:9d} | {r['dfs_count']:>5d}/100 |")
        else:
            print(f"| {size_part} | {diff_part:6s} | {r['total']:6d} | {'─':>7s} | {'─':>9s} | {'─':>9s} | {'─':>7s} |")


if __name__ == "__main__":
    main()
