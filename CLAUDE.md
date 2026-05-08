# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run**: `uv run python main.py`
- **Fetch + solve**: `uv run python main.py --fetch`
- **Fetch by size/difficulty**: `uv run python main.py --size 10 --fetch`
- **Fetch by puzzle ID**: `uv run python main.py --size 10 --id 5`
- **Daily/weekly/monthly**: `uv run python main.py --daily`
- **Time limit**: `uv run python main.py --time 5.0`
- **Print puzzle only**: `uv run python main.py --size 15 -p`
- **Sync env**: `uv sync`

## Project Structure

- `main.py` — CLI, argument parsing, puzzle fetching from `cn.puzzle-yin-yang.com`
- `yinyang_solver.py` — Solver engine (`Solver` class + `decode` helper)
- `pyproject.toml` — Project metadata, Python ≥3.12, depends only on `requests`

No test framework or tests configured yet.

## Architecture

### Solver Algorithm Flow (`Solver` in `yinyang_solver.py`)

**State representation**: 0=UNKNOWN, 1=WHITE, 2=BLACK. Undo stack (list of `(r,c,old_val)`) instead of deepcopy — `_snap()` / `_ba()` saves/restores stack position.

**`solve()` → `_propagate()` → `_dfs()` → `_ok()`**

1. **Propagation loop** (`_propagate`): Alternates 2×2 rule and bridge rule until stable, returns False on conflict.
2. **DFS** (`_dfs`): Picks a cell via `_pick()`, tries WHITE/BLACK (ordered by neighbor majority), recurses. On timeout → False. On leaf (no unknowns) → `_ok()` verifies full connectivity.
3. **Cell selection** (`_pick`): MRV heuristic — prefers cells on boundaries of multi-component colors (score ×1000), then single-component boundaries (×100), then most-constrained unknown cell. Smallest components are prioritized (they need to grow the most).

### Propagation Rules

- **Rule 1 — 2×2 same-color** (`_p2`): If any 2×2 block has 3 cells of the same color, the 4th is forced to the opposite color.
- **Rule 2 — 2×2 diagonal** (`_p2`): If a 2×2 block has a diagonal pair of color C and one remaining cell is the opposite color O, the last cell must be C.
- **Rule 3 — Perimeter contiguity** (`_perimeter`): On the outer boundary, same-color cells form contiguous arcs. If two cells of color C are on the perimeter with no opposite color between them, all unknowns on that arc are forced to C (unless it creates a 2×2 violation). Prevents C...O...C patterns on the perimeter.
- **Bridge rule** (`_bridge`): If a color has 2+ connected components and a component has exactly 1 unknown boundary cell, that cell is forced to the component's color. 0 boundary → conflict. Total boundary < k−1 → impossible to connect. Includes fast early-exit when both colors already form 1 component each.
- **Connectivity check** (`_conn`): Full BFS per color, only at leaf nodes (when all cells assigned).

### Task String RLE Format

Puzzles from the website use run-length encoding:
- Uppercase `W` = one white cell, `B` = one black cell
- Lowercase `a`-`z` = 1–26 consecutive unknown cells each

Example: `'BcBaBBWfWdWaWdBh'` decodes to a 6×6 grid with 9 given cells (5 black, 4 white).

The `decode(task, N)` function produces `list[list[int]]` for use by the solver.

### Size Map (cn.puzzle-yin-yang.com)

`?size=N` parameter maps to puzzle dimensions:
- `0`/`1`/`2` → 6×6 (easy/normal/hard)
- `3`/`4`/`5` → 10×10
- `6`/`7`/`8` → 15×15
- `9`/`10`/`11` → 20×20
- `12`/`13`/`14` → 25×25
- `15` = 30×30 (daily), `16` = 35×35 (weekly), `17` = 40×40 (monthly)

CLI `--size` uses human keys (`6`, `10`, `15`, `20`, `25`) with optional difficulty suffix (`e`/`n`/`h`).

### Performance Expectations

| Size | Typical | Notes |
|------|---------|-------|
| 6×6 | < 1ms | Pure deduction, 0 DFS nodes |
| 10×10 | < 5ms | 0–11 DFS nodes |
| 15×15 | < 10ms | 0–5 DFS nodes |
| 20×20 normal | < 25ms | 0–12 DFS nodes |
| 20×20 hard | may time out | Many scattered components, bridge rule can't fire |
| 25×25 | < 1.5s | 0–400 DFS nodes |

Puzzles where both colors have many small components (10+ each) are the hardest because each component has ≥2 boundary cells, preventing the bridge rule from firing. The DFS then has too many degrees of freedom.

### Visualization

Terminal output uses ANSI escape codes:
- White background + black text for WHITE cells
- Black background + white text for BLACK cells
- Gray background for UNKNOWN cells
- Column/row headers with bold formatting
- Verification status with ✓/✗ markers
