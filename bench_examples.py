"""Run each example 05-09 10 times and print average results."""
import subprocess
import json
import re
import glob
import os

examples = sorted(glob.glob("examples/example0[5-9].json"))

for path in examples:
    name = os.path.splitext(os.path.basename(path))[0]
    times = []
    traces = []
    nodes = []
    for _ in range(10):
        try:
            r = subprocess.run(
                ["uv", "run", "python", "main.py", "--load", path],
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            print(f"{name}: timeout on iteration {len(times)+1}")
            continue
        plain = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', r.stdout + r.stderr)
        m_t = re.search(r'时间=([\d.]+)', plain)
        m_tr = re.search(r'trace=(\d+)', plain)
        m_n = re.search(r'节点=(\d+)', plain)
        if m_t: times.append(float(m_t.group(1)))
        if m_tr: traces.append(int(m_tr.group(1)))
        if m_n: nodes.append(int(m_n.group(1)))

    avg_t = sum(times) / len(times) * 1000 if times else 0
    avg_tr = sum(traces) / len(traces) if traces else 0
    max_n = max(nodes) if nodes else 0

    with open(path) as f:
        data = json.load(f)
    size = f"{data['puzzleWidth']}×{data['puzzleHeight']}"
    dfs = "✓" if data.get("need_dfs") else ""

    print(f"{name:13s} | {size:8s} | {avg_t:6.0f}ms | {avg_tr:6.0f} | {max_n:4d} | {dfs}")
