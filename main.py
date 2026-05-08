"""
Yin-Yang Puzzle Solver - CLI

Usage:
    uv run python main.py                     # 示例谜题 (6x6)
    uv run python main.py --fetch             # 随机谜题
    uv run python main.py --size 10           # 指定大小
    uv run python main.py --id 5              # 指定编号
    uv run python main.py --daily             # 每日谜题
    uv run python main.py -p 10x10            # 直接打印指定谜题
"""

import sys
import json
import re
import time
import requests

from yinyang_solver import Solver, decode, solve


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
    'daily': '12',
    'weekly': '13',
    'monthly': '14',
}


def fetch_puzzle(url: str) -> tuple[str | None, int, int, str | None]:
    """
    从网站获取谜题数据

    Returns:
        (task_str, width, height, puzzle_id) 或 (None, 0, 0, None)
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
        else:
            date_m = re.search(r'<option[^>]+selected="selected"[^>]*>\s*([A-Za-z]+\s+\d+,\s*\d+)\s*</option>', html)
            if date_m:
                pid = date_m.group(1).strip()

        return task, width, height, pid

    except Exception as e:
        print(f"获取谜题失败: {e}")
        return None, 0, 0, None


def fetch_by_id(size_param: str, puzzle_id: int) -> tuple[str | None, int, int, str | None]:
    """通过 POST 获取指定编号的谜题"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        r = requests.post(
            "https://cn.puzzle-yin-yang.com/",
            headers=headers,
            data=f"specific=1&size={size_param}&specid={puzzle_id}",
            timeout=30,
        )
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

        return task, width, height, pid

    except Exception as e:
        print(f"获取谜题失败: {e}")
        return None, 0, 0, None


def get_puzzle(size_key: str = "6") -> tuple[list[list[int]] | None, int, str | None]:
    """获取谜题"""
    size_param = SIZE_MAP.get(size_key, '1')
    url = f"https://cn.puzzle-yin-yang.com/?size={size_param}"
    task, w, h, pid = fetch_puzzle(url)
    if task and w > 0 and h > 0:
        grid = decode(task, w)
        print(f"获取到 {w}x{h} 谜题 (ID: {pid or '?'})")
        return grid, w, pid
    print("获取谜题失败")
    return None, 0, None


def print_puzzle(grid):
    """纯文本打印谜题"""
    s = Solver()
    s.load(grid)
    print(f"\n{s.N}x{s.N} 谜题:")
    s.pc()


def main():
    # Default: show example
    size = "6"
    use_fetch = '--fetch' in sys.argv or '-f' in sys.argv
    use_daily = '--daily' in sys.argv
    use_weekly = '--weekly' in sys.argv
    use_monthly = '--monthly' in sys.argv
    puzzle_id = None
    print_only = '-p' in sys.argv
    time_limit = 10.0
    no_color = '--no-color' in sys.argv

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
        else:
            i += 1

    grid = None
    N = 0

    if use_daily:
        print("获取每日谜题...")
        grid, N, pid = get_puzzle('daily')
    elif use_weekly:
        print("获取每周谜题...")
        grid, N, pid = get_puzzle('weekly')
    elif use_monthly:
        print("获取每月谜题...")
        grid, N, pid = get_puzzle('monthly')
    elif use_fetch or puzzle_id is not None:
        if puzzle_id is not None:
            size_param = SIZE_MAP.get(size, '1')
            print(f"获取谜题 (size={size}, id={puzzle_id})...")
            try:
                s = requests.Session()
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                r = s.post("https://cn.puzzle-yin-yang.com/",
                          headers=headers,
                          data=f"specific=1&size={size_param}&specid={puzzle_id}",
                          timeout=30)
                html = r.text
                task_m = re.search(r"var\s+task\s*=\s*'([^']+)'", html)
                w_m = re.search(r'puzzleWidth\s*:\s*(\d+)', html)
                if task_m and w_m:
                    task = task_m.group(1)
                    w = int(w_m.group(1))
                    h_m = re.search(r'puzzleHeight\s*:\s*(\d+)', html)
                    h = int(h_m.group(1)) if h_m else w
                    grid = decode(task, w)
                    N = w
                    print(f"获取到 {w}x{h} 谜题 (ID: {puzzle_id})")
                else:
                    print("未找到谜题数据")
            except Exception as e:
                print(f"获取失败: {e}")
        else:
            grid, N, pid = get_puzzle(size)
    else:
        # Example puzzle (6x6)
        print("使用示例谜题 (6x6)")
        grid = decode('BcBaBBWfWdWaWdBh', 6)
        N = 6

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
    solver = Solver(time_limit=time_limit)
    solver.load(grid)
    print(f"\n求解 {solver.N}x{solver.N} Yin-Yang 谜题...")
    solver.pc()

    t0 = time.time()
    ok = solver.solve()
    elapsed = time.time() - t0

    if ok:
        solver.ps()
    else:
        print(f"\n❌ 未找到解 (节点: {solver.nodes}, 用时: {elapsed:.3f}s)")


if __name__ == "__main__":
    main()
