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

# 自定义动画间隔（毫秒，默认 10ms）
uv run python main.py --trace --trace-delay 50
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

DFS 选择最小多分量颜色的边界格优先，结合桥评分启发式。

## 谜题格式

网站下发的 task 为 RLE 编码：
- `W` / `B` — 一个白色/黑色格
- `a`-`z` — 1-26 个连续空格

`decode(task, N)` 解码为 `list[list[int]]`。

## 文件结构

- `main.py` — CLI 入口，谜题获取
- `yinyang_solver.py` — 求解器（Solver 类）
- `pyproject.toml` — 项目配置（Python ≥3.12，依赖 requests）

## 性能

测试条件：从 `puzzles_all.json`（随机获取的 1500 个可解谜题，每个尺寸/难度 100 个）读取并求解。

测试环境：Intel(R) Core(TM) Ultra 9 275HX (24 cores)，Python 3.12

| 尺寸 | 难度 | 平均耗时 | 平均 trace | 最大 trace | 需 DFS |
|------|------|---------|-----------|-----------|--------|
| 6×6 | easy | 0.57ms | 26 | 29 | 0/100 |
| 6×6 | normal | 0.66ms | 59 | 427 | 0/100 |
| 6×6 | hard | 1.40ms | 192 | 902 | 0/100 |
| 10×10 | easy | 2.49ms | 69 | 76 | 0/100 |
| 10×10 | normal | 2.83ms | 247 | 3,408 | 0/100 |
| 10×10 | hard | 4.57ms | 533 | 2,764 | 0/100 |
| 15×15 | easy | 7.50ms | 153 | 164 | 0/100 |
| 15×15 | normal | 6.22ms | 445 | 2,694 | 0/100 |
| 15×15 | hard | 14.04ms | 1,672 | 24,902 | 1/100 |
| 20×20 | easy | 16.84ms | 258 | 279 | 0/100 |
| 20×20 | normal | 12.64ms | 917 | 5,298 | 0/100 |
| 20×20 | hard | 27.62ms | 2,674 | 14,192 | 0/100 |
| 25×25 | easy | 29.27ms | 389 | 414 | 0/100 |
| 25×25 | normal | 30.15ms | 2,178 | 42,421 | 0/100 |
| 25×25 | hard | 56.99ms | 5,511 | 75,956 | 2/100 |

1500 个随机谜题中仅 3 个需要 DFS（15×15 hard ×1、25×25 hard ×2），其余均为纯推理完成。

## 测试用例

`examples/` 目录包含九个典型谜题文件，可通过 `--load` 加载测试：

测试环境：Intel(R) Core(TM) Ultra 9 275HX (24 cores)

```bash
uv run python main.py --load examples/example01.json   # 30×30（每日）
uv run python main.py --load examples/example02.json   # 35×35（每周）
uv run python main.py --load examples/example03.json   # 40×40（每月）
uv run python main.py --load examples/example04.json   # 25×25 hard（纯推理，~38ms）
uv run python main.py --load examples/example05.json   # 25×25 hard（纯推理，~224ms）
uv run python main.py --load examples/example06.json   # 25×25 hard（纯推理，~106ms）
uv run python main.py --load examples/example07.json   # 25×25 hard（纯推理，~77ms）
uv run python main.py --load examples/example08.json   # 25×25 hard（需 DFS，~183ms）
uv run python main.py --load examples/example09.json   # 25×25 hard（纯推理，~59ms）
```

| 文件 | 尺寸 | 耗时（10次平均） | trace | 节点 |
|------|------|-------------------|-------|------|
| example01 | 30×30 | 52ms | 5188 | 0 |
| example02 | 35×35 | 99ms | 10849 | 0 |
| example03 | 40×40 | 114ms | 9854 | 0 |
| example04 | 25×25 hard | 39ms | 4421 | 0 |
| example05 | 25×25 hard | 224ms | 28236 | 0 |
| example06 | 25×25 hard | 106ms | 15180 | 0 |
| example07 | 25×25 hard | 77ms | 8394 | 0 |
| example08 | 25×25 hard | 183ms | 28594 | 29 |
| example09 | 25×25 hard | 59ms | 7258 | 0 |
