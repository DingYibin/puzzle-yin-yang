"""
Batch fetch puzzles by ID (11-100) for size 25h.
Save all, copy DFS/slow ones to examples/.
"""
import subprocess
import json
import os
import re
import glob

SIZE = "25h"
EXAMPLES_DIR = "examples"
PUZZLES_DIR = "puzzles"
os.makedirs(EXAMPLES_DIR, exist_ok=True)

# Determine next example number
existing = sorted(glob.glob(os.path.join(EXAMPLES_DIR, "example*.json")))
next_num = 1
if existing:
    last = existing[-1]
    m = re.search(r'example(\d+)', os.path.basename(last))
    if m:
        next_num = int(m.group(1)) + 1

results = []


def parse_output(output: str) -> tuple[bool, int, float]:
    """Parse solver output to extract success, nodes, elapsed time."""
    plain = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
    nodes = 0
    elapsed = 0.0
    ok = False
    m_nodes = re.search(r'节点=(\d+)', plain)
    m_time = re.search(r'时间=([\d.]+)', plain)
    if m_nodes:
        nodes = int(m_nodes.group(1))
    if m_time:
        elapsed = float(m_time.group(1))
    # Success if the last occurrence of 节点= is on a line with ✓
    for line in reversed(plain.split('\n')):
        if '节点=' in line:
            ok = '✓' in line
            break
    return ok, nodes, elapsed


for pid in range(11, 101):
    print(f"--- ID {pid} ---")
    try:
        r = subprocess.run(
            ["uv", "run", "python", "main.py", "--size", SIZE, "--id", str(pid), "--save"],
            capture_output=True, text=True, timeout=120,
        )
        ok, nodes, elapsed = parse_output(r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        print(f"  ID {pid}: timeout")
        ok, nodes, elapsed = False, 0, 0.0

    need_dfs = nodes > 0
    slow = elapsed > 0.3

    flags = []
    if need_dfs:
        flags.append("DFS")
    if slow:
        flags.append(f"SLOW({elapsed:.3f}s)")
    flag_str = f" [{', '.join(flags)}]" if flags else ""

    print(f"  -> ok={ok} nodes={nodes} time={elapsed:.3f}s{flag_str}")

    rec = {"id": pid, "ok": ok, "nodes": nodes, "elapsed": elapsed, "need_dfs": need_dfs, "slow": slow}
    results.append(rec)

    # If DFS or slow, copy latest puzzle to examples
    # Parse the saved file path from main.py output instead of guessing by mtime
    if need_dfs or slow:
        saved_path = None
        for line in reversed((r.stdout + r.stderr).split('\n')):
            m = re.search(r'谜题已保存到\s+(.+\.[a-zA-Z]+)', line)
            if m:
                saved_path = m.group(1).strip()
                break
        if saved_path and os.path.exists(saved_path):
            dest = os.path.join(EXAMPLES_DIR, f"example{next_num:02d}.json")
            with open(saved_path) as f:
                data = json.load(f)
            data["need_dfs"] = need_dfs
            data["puzzleSize"] = SIZE
            data["puzzleId"] = str(pid)
            with open(dest, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  -> copied to {dest}")
            next_num += 1

# Summary
print()
print("=" * 60)
total = len(results)
ok_count = sum(1 for r in results if r["ok"])
dfs_count = sum(1 for r in results if r["need_dfs"])
slow_count = sum(1 for r in results if r["slow"])
print(f"Summary:")
print(f"  Total: {total}")
print(f"  Solved OK: {ok_count}")
print(f"  Need DFS: {dfs_count}")
print(f"  Slow (>300ms): {slow_count}")
print()
print("Detail:")
for r in results:
    flags = []
    if r["need_dfs"]:
        flags.append("DFS")
    if r["slow"]:
        flags.append(f"{r['elapsed']:.3f}s")
    flag_str = f" [{', '.join(flags)}]" if flags else ""
    status = "✓" if r["ok"] else "✗"
    print(f"  ID {r['id']:3d}: {status} nodes={r['nodes']:4d} time={r['elapsed']:.3f}s{flag_str}")
