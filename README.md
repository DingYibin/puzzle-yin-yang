# Yin-Yang Puzzle Solver (阴阳谜题求解器)

DFS 求解器，自动从 [cn.puzzle-yin-yang.com](https://cn.puzzle-yin-yang.com/) 获取谜题并求解，支持彩色终端可视化。

本求解器使用 [Claude Code](https://claude.ai/code) 调用 DeepSeek-v4-flash API 开发完成。

## 规则

- 每个格子填入白色（○）或黑色（●）
- 所有白色格子必须四连通
- 所有黑色格子必须四连通
- 没有 2×2 区域全是同色

## 使用方法

```bash
# 随机谜题 (默认 6×6)
uv run python main.py

# 指定大小
uv run python main.py --size 10

# 指定编号
uv run python main.py --size 10 --id 5

# 每日/每周/每月谜题
uv run python main.py --daily
uv run python main.py --weekly
uv run python main.py --monthly

# 从本地文件加载
uv run python main.py --load examples/example01.json

# 求解动画（干净步骤 / 含回溯）
uv run python main.py --trace
uv run python main.py --trace-full

# 禁用 DFS（纯推理）
uv run python main.py --no-dfs
```

## 求解策略

四个传播规则 + DFS：

| # | 规则 | 说明 |
|---|------|------|
| 1 | **2×2 三同色** | 2×2 块内有 3 格同色 → 第 4 格为异色 |
| 2 | **2×2 对角** | 对角同色 + 一角异色 → 最后一角为对角颜色 |
| 3 | **外围连续** | 外围同色格形成连续弧段，中间空格自动填充 |
| 4 | **四邻同色** | 未知格所有邻格均已知且同色 → 该格也为此色 |

BFS 桥规则（`_bfs_comp`）：单元格赋值时立即检查同色及反色连通分量，若某分量仅 1 个未知边界 → 强制赋值。

Union-Find 桥规则（`_connectivity_expand` 预处理）：扫描全图连通分量，找不到边界 → 冲突；恰好 1 个边界 → 强制赋值。

Try-both 对立色连通检查（`_check_opposite_connectivity_at`）：每个 try 分支中，从已染色 cell 出发，检查其周围的对立色 cell 是否能通过 UNKNOWN 保持连通。若 2+ 个对立色 cell 被阻断 → 该分支非法。大幅减少 DFS 节点数。

DFS 选择最小多分量颜色的边界格优先，结合桥评分启发式。可通过 `--no-dfs` 禁用。

## 谜题格式

网站下发的 task 为 RLE 编码：
- `W` / `B` — 一个白色/黑色格
- `a`-`z` — 1-26 个连续空格

`decode(task, N)` 解码为 `list[list[int]]`。

保存的 JSON 文件增加 `need_dfs` 字段，标明求解时是否触发了 DFS。

## 文件结构

- `main.py` — CLI 入口，谜题获取
- `yinyang_solver.py` — 求解器（Solver 类）
- `pyproject.toml` — 项目配置（Python ≥3.12，依赖 requests）

## 性能

测试条件：每个尺寸/难度组合取 ID 1–10 共 10 个谜题，求解后取平均（网站谜题，节点数均为 0）。

| 尺寸 | 难度 | 平均耗时 | 平均 trace |
|------|------|---------|-----------|
| 6×6 | easy | 2ms | 25 |
| 6×6 | normal | 2ms | 39 |
| 6×6 | hard | 4ms | 228 |
| 10×10 | easy | 5ms | 70 |
| 10×10 | normal | 6ms | 191 |
| 10×10 | hard | 9ms | 323 |
| 15×15 | easy | 16ms | 152 |
| 15×15 | normal | 22ms | 834 |
| 15×15 | hard | 17ms | 593 |
| 20×20 | easy | 33ms | 255 |
| 20×20 | normal | 34ms | 878 |
| 20×20 | hard | 58ms | 2,423 |
| 25×25 | easy | 63ms | 389 |
| 25×25 | normal | 63ms | 1,810 |
| 25×25 | hard | 114ms | 4,465 |
| 30×30 (每日) | — | ~140ms | ~5.5k |
| 35×35 (每周) | — | ~277ms | ~11k |
| 40×40 (每月) | — | ~296ms | ~10k |

复杂 20×20（散落线索较多）可能需 DFS 或超时。25×25 hard 平均 trace ≈ 4.5k，偶见需 DFS 的极端谜题。

## 测试用例

`examples/` 目录包含九个典型谜题文件，可通过 `--load` 加载测试：

测试环境：Intel(R) Core(TM) Ultra 9 275HX (24 cores)

```bash
uv run python main.py --load examples/example01.json   # 30×30（每日）
uv run python main.py --load examples/example02.json   # 35×35（每周）
uv run python main.py --load examples/example03.json   # 40×40（每月）
uv run python main.py --load examples/example04.json   # 25×25 hard（纯推理，约 60ms）
uv run python main.py --load examples/example05.json   # 25×25 hard（纯推理，约 396ms）
uv run python main.py --load examples/example06.json   # 25×25 hard（纯推理，约 172ms）
uv run python main.py --load examples/example07.json   # 25×25 hard（纯推理，约 115ms）
uv run python main.py --load examples/example08.json   # 25×25 hard（需 DFS，约 743ms）
uv run python main.py --load examples/example09.json   # 25×25 hard（纯推理，约 99ms）
```

| 文件 | 尺寸 | 耗时（10次平均） | trace | 节点 |
|------|------|-------------------|-------|------|
| example01 | 30×30 | 140ms | 5478 | 0 |
| example02 | 35×35 | 277ms | 11015 | 0 |
| example03 | 40×40 | 296ms | 10084 | 0 |
| example04 | 25×25 hard | 60ms | 4287 | 0 |
| example05 | 25×25 hard | 396ms | 27562 | 0 |
| example06 | 25×25 hard | 172ms | 14874 | 0 |
| example07 | 25×25 hard | 115ms | 7900 | 0 |
| example08 | 25×25 hard | 743ms | 68372 | 1748 |
| example09 | 25×25 hard | 99ms | 7602 | 0 |
