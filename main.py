"""
Yin-Yang Puzzle Solver — CLI

Usage:
    uv run python main.py                     # Random 6×6 puzzle
    uv run python main.py --size 10           # Specify size (6, 10, 15, 20, 25, 30, 35, 40)
    uv run python main.py --id 5              # Puzzle by ID
    uv run python main.py --daily             # Daily puzzle
    uv run python main.py --load path.json    # Load from file
    uv run python main.py -p                  # Print puzzle only (no solve)
"""

import sys
import json
import re
import time
import os
from datetime import datetime
import requests

from yinyang_solver import Solver, decode, encode, solve


# Size parameter mapping (cn.puzzle-yin-yang.com)
SIZE_MAP = {
    '6': '1',       # 6x6 normal
    '6e': '0',      # 6x6 easy
    '6n': '1',      # 6x6 normal
    '6h': '2',      # 6x6 hard
    '10': '4',      # 10x10 normal
    '10e': '3',     # 10x10 easy
    '10n': '4',     # 10x10 normal
    '10h': '5',     # 10x10 hard
    '15': '7',      # 15x15 normal
    '15e': '6',     # 15x15 easy
    '15n': '7',     # 15x15 normal
    '15h': '8',     # 15x15 hard
    '20': '10',     # 20x20 normal
    '20e': '9',     # 20x20 easy
    '20n': '10',    # 20x20 normal
    '20h': '11',    # 20x20 hard
    '25': '13',     # 25x25 normal
    '25e': '12',    # 25x25 easy
    '25n': '13',    # 25x25 normal
    '25h': '14',    # 25x25 hard
    '30': '15',     # 30x30 (daily)
    '35': '16',     # 35x35 (weekly)
    '40': '17',     # 40x40 (monthly)
    'daily': '15',
    'weekly': '16',
    'monthly': '17',
}


def fetch_puzzle(url: str) -> tuple:
    """
    从网站获取谜题数据

    Returns:
        (task_str, width, height, puzzle_id, selected_date)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        html = r.text

        task_m = re.search(r"var\s+task\s*=\s*'([^']+)'", html)
        task = task_m.group(1) if task_m else None

        w_m = re.search(r'puzzleWidth\s*:\s*(\d+)', html)
        h_m = re.search(r'puzzleHeight\s*:\s*(\d+)', html)
        width = int(w_m.group(1)) if w_m else 0
        height = int(h_m.group(1)) if h_m else 0

        pid = None
        id_m = re.search(r'id="puzzleID"\s*>\s*([0-9,]+)', html)
        if id_m:
            pid = id_m.group(1)

        selected_date = None
        date_m = re.search(r'<option\s+value="([^"]*)"[^>]*selected="selected"', html)
        if date_m:
            selected_date = date_m.group(1).strip()
        if not selected_date:
            date_m = re.search(r'<option[^>]+selected="selected"[^>]*>\s*([A-Za-z]+\s+\d+,\s*\d+)\s*</option>', html)
            if date_m:
                selected_date = date_m.group(1).strip()

        return task, width, height, pid, selected_date

    except Exception as e:
        print(f"获取谜题失败: {e}")
        return None, 0, 0, None, None


def fetch_by_id(size_param: str, puzzle_id: int) -> tuple[str | None, int, int, str | None]:
    """通过 POST 获取指定编号的谜题"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        s = requests.Session()
        r = s.post(
            "https://cn.puzzle-yin-yang.com/",
            headers=headers,
            data=f"specific=1&size={size_param}&specid={puzzle_id}",
            timeout=30,
        )
        html = r.text
        task_m = re.search(r"var\s+task\s*=\s*'([^']+)'", html)
        w_m = re.search(r'puzzleWidth\s*:\s*(\d+)', html)
        if task_m and w_m:
            task = task_m.group(1)
            w = int(w_m.group(1))
            h_m = re.search(r'puzzleHeight\s*:\s*(\d+)', html)
            h = int(h_m.group(1)) if h_m else w
            pid = None
            id_m = re.search(r'id="puzzleID"\s*>\s*([0-9,]+)', html)
            if id_m:
                pid = id_m.group(1)
            return task, w, h, pid
        return None, 0, 0, None
    except Exception as e:
        print(f"获取谜题失败: {e}")
        return None, 0, 0, None


def get_puzzle(size_key: str = "6") -> tuple:
    """获取谜题, 返回 (grid, N, pid, selected_date, size_key)"""
    size_param = SIZE_MAP.get(size_key, '1')
    url = f"https://cn.puzzle-yin-yang.com/?size={size_param}"
    task, w, h, pid, sel_date = fetch_puzzle(url)
    if task and w > 0 and h > 0:
        grid = decode(task, w)
        print(f"获取到 {w}x{h} 谜题 (ID: {pid or '?'})")
        return grid, w, pid, sel_date, size_key
    print("获取谜题失败")
    return None, 0, None, None, None


def print_puzzle(grid):
    """纯文本打印谜题"""
    s = Solver()
    s.load(grid)
    print(f"\n{s.N}x{s.N} 谜题:")
    s.pc()


def save_puzzle(grid, **extra):
    """保存谜题到 puzzles/<timestamp>.json"""
    task = encode(grid)
    w = len(grid)
    h = len(grid[0]) if grid else w
    data = {"task": task, "puzzleWidth": w, "puzzleHeight": h, **extra}
    filename = "puzzle-yin-yang_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    os.makedirs("puzzles", exist_ok=True)
    filepath = os.path.join("puzzles", filename)
    with open(filepath, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"谜题已保存到 {filepath}")
    return filepath


def load_puzzle(path):
    """从 JSON 文件加载谜题"""
    with open(path) as f:
        data = json.load(f)
    task = data["task"]
    w = data["puzzleWidth"]
    h = data.get("puzzleHeight", w)
    grid = decode(task, w)
    print(f"从 {path} 加载 {w}x{h} 谜题")
    return grid


def main():
    size = "6"
    use_daily = '--daily' in sys.argv
    use_weekly = '--weekly' in sys.argv
    use_monthly = '--monthly' in sys.argv
    puzzle_id = None
    print_only = '-p' in sys.argv
    time_limit = 10.0
    no_color = '--no-color' in sys.argv
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    no_dfs = '--no-dfs' in sys.argv
    trace = '--trace' in sys.argv
    trace_full = '--trace-full' in sys.argv
    trace_delay = None  # ms
    use_save = '--save' in sys.argv
    load_path = None

    # Parse args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ('--size', '-s') and i + 1 < len(args):
            size = args[i + 1]
            i += 2
        elif args[i] in ('--id', '-n') and i + 1 < len(args):
            try:
                puzzle_id = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == '--time' and i + 1 < len(args):
            try:
                time_limit = float(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] == '--load' and i + 1 < len(args):
            load_path = args[i + 1]
            i += 2
        elif args[i] == '--trace-delay' and i + 1 < len(args):
            try:
                trace_delay = float(args[i + 1])
            except ValueError:
                print("警告: --trace-delay 需要数值参数（毫秒）")
            i += 2
        else:
            i += 1

    grid = None
    N = 0
    loaded_from_file = False
    puzzle_meta = {}

    if load_path:
        grid = load_puzzle(load_path)
        N = len(grid) if grid else 0
        loaded_from_file = True
    elif use_daily:
        print("获取每日谜题...")
        grid, N, pid, sel_date, sk = get_puzzle('daily')
        puzzle_meta = {"puzzleSize": sk, "puzzleId": pid, "puzzleDate": sel_date}
    elif use_weekly:
        print("获取每周谜题...")
        grid, N, pid, sel_date, sk = get_puzzle('weekly')
        puzzle_meta = {"puzzleSize": sk, "puzzleId": pid, "puzzleDate": sel_date}
    elif use_monthly:
        print("获取每月谜题...")
        grid, N, pid, sel_date, sk = get_puzzle('monthly')
        puzzle_meta = {"puzzleSize": sk, "puzzleId": pid, "puzzleDate": sel_date}
    elif puzzle_id is not None:
        size_param = SIZE_MAP.get(size, '1')
        print(f"获取谜题 (size={size}, id={puzzle_id})...")
        task, w, h, pid = fetch_by_id(size_param, puzzle_id)
        if task and w > 0:
            grid = decode(task, w)
            N = w
            puzzle_meta = {"puzzleSize": size, "puzzleId": str(puzzle_id)}
            print(f"获取到 {w}x{h} 谜题 (ID: {puzzle_id})")
        else:
            print("未找到谜题数据")
    else:
        grid, N, pid, sel_date, sk = get_puzzle(size)
        puzzle_meta = {"puzzleSize": sk, "puzzleId": pid, "puzzleDate": sel_date}

    if grid is None:
        print("没有谜题可求解")
        return

    if print_only:
        print_puzzle(grid)
        return

    if no_color:
        # Override terminal codes
        pass

    # Solve
    solver = Solver(time_limit=time_limit, verbose=verbose, dfs_enabled=not no_dfs)
    solver.load(grid)
    solver._puzzle_meta = puzzle_meta
    print(f"\n求解 {solver.N}x{solver.N} Yin-Yang 谜题...")
    solver.pc()

    t0 = time.time()
    ok = solver.solve(save_on_fail=not loaded_from_file and not use_save)
    elapsed = time.time() - t0

    if ok:
        delay_sec = trace_delay / 1000.0 if trace_delay is not None else None
        if trace_full:
            solver.animate(full_trace=True, delay=delay_sec)
        elif trace:
            solver.animate(delay=delay_sec)
        solver.ps(elapsed=elapsed)
    else:
        print(f"\n❌ 未找到解 (节点: {solver.nodes}, 用时: {elapsed:.3f}s)")
        if not loaded_from_file:
            save_puzzle(grid, need_dfs=True, **puzzle_meta)

    if use_save and ok:
        save_puzzle(grid, need_dfs=solver.nodes > 0, **puzzle_meta)


if __name__ == "__main__":
    main()
