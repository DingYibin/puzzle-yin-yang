# Yin-Yang Puzzle Solver (阴阳谜题求解器)

DFS 求解器，自动从 [cn.puzzle-yin-yang.com](https://cn.puzzle-yin-yang.com/) 获取谜题并求解，支持彩色终端可视化。

## 规则

- 每个格子填入白色（○）或黑色（●）
- 所有白色格子必须四连通
- 所有黑色格子必须四连通
- 没有 2×2 区域全是同色

## 使用方法

```bash
# 示例谜题 (6x6)
uv run python main.py

# 从网站获取随机谜题
uv run python main.py --fetch

# 指定大小
uv run python main.py --size 10 --fetch

# 指定编号
uv run python main.py --size 10 --id 5

# 每日/每周/每月谜题
uv run python main.py --daily
uv run python main.py --weekly
uv run python main.py --monthly

# 从本地文件加载
uv run python main.py --load examples/example01.json
```

## 求解策略

四个传播规则 + DFS：

| # | 规则 | 说明 |
|---|------|------|
| 1 | **2×2 三同色** | 2×2 块内有 3 格同色 → 第 4 格为异色 |
| 2 | **2×2 对角** | 对角同色 + 一角异色 → 最后一角为对角颜色 |
| 3 | **外围连续** | 外围同色格形成连续弧段，中间空格自动填充 |
| 4 | **四邻同色** | 未知格所有邻格均已知且同色 → 该格也为此色 |

桥规则：同色连通分量仅 1 个未知边界 → 强制赋值。

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

| 尺寸 | 典型耗时 | 搜索节点 |
|------|----------|----------|
| 6×6 | < 1ms | 0 |
| 10×10 | < 5ms | 0–11 |
| 15×15 | < 15ms | 0–8 |
| 20×20 | < 200ms | 0–136 |
| 25×25 | ~1.5s | 0–400 |
| 30×30（每日） | ~300ms | 0 |
| 35×35（每周） | ~900ms | 0 |
| 40×40（每月） | ~650ms | 0 |

复杂 20×20（散落线索较多）可能超时。

## 测试用例

`examples/` 目录包含三个典型谜题文件，可通过 `--load` 加载测试：

```bash
uv run python main.py --load examples/example01.json   # 30×30（每日）
uv run python main.py --load examples/example02.json   # 35×35（每周）
uv run python main.py --load examples/example03.json   # 40×40（每月）
```

| 文件 | 尺寸 | 耗时 |
|------|------|------|
| example01 | 30×30 | 300ms |
| example02 | 35×35 | 905ms |
| example03 | 40×40 | 652ms |
