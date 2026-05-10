# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run**: `uv run python main.py` (ships with a 6×6 example)
- **Fetch + solve**: `uv run python main.py --fetch` (random puzzle, default 6×6)
- **Fetch by size**: `uv run python main.py --size 10 --fetch` (sizes: 6, 10, 15, 20, 25; difficulty suffix e/n/h)
- **Fetch by puzzle ID**: `uv run python main.py --size 10 --id 5`
- **Daily/weekly/monthly**: `uv run python main.py --daily` / `--weekly` / `--monthly`
- **Load from JSON**: `uv run python main.py --load puzzles/file.json`
- **Save puzzle**: `uv run python main.py --fetch --save`
- **Time limit**: `uv run python main.py --time 10.0` (default 10.0s)
- **Verbose mode**: `uv run python main.py --verbose` (prints grid state at each step)
- **Print puzzle only**: `uv run python main.py --size 15 -p`
- **Sync env**: `uv sync`

## Project Structure

- `main.py` — CLI, argument parsing, puzzle fetching from `cn.puzzle-yin-yang.com`
- `yinyang_solver.py` — Solver engine (`Solver` class + `decode`/`encode` helpers)
- `pyproject.toml` — Project metadata, Python ≥3.12, depends only on `requests`
- `puzzles/` — Auto-saved puzzles (when DFS is needed, or on failure)

No test framework or tests configured yet.

## Architecture

### Solver Algorithm Flow (`Solver` in `yinyang_solver.py`)

**State representation**: 0=UNKNOWN, 1=WHITE, 2=BLACK. Undo stack (list of `(r,c,old_val)`) instead of deepcopy — `_sn()` / `_ba()` saves/restores stack position. Counters `_wc`/`_bc`/`_uc` maintained incrementally by `_set()` and `_ba()`.

**`solve()` → preprocessing → try_both loop → `_dfs()` → `_ok()`**

**Preprocessing** (in order):
1. `_p2()` — Full-grid 2×2 deduction (Rules 1 & 2)
2. `_corner3()` — 2×3/3×2 corner deduction (Rule 5)
3. `_surrounded()` — Surrounded cell / single unknown exit (Rule 4)
4. `_conn_expand()` — Union-Find bridge rule (connectivity-driven forcing)
5. `_propagate()` — Alternates `_perimeter()` and `_conn_expand()` until stable

**Try-both** (`_try_both`): For each unknown cell, try WHITE then BLACK with full propagation. If exactly one color works, force it. If both conflict → unsolvable. Loops until no more forced cells.

**DFS** (`_dfs`): Picks a cell via `_pick()`, tries WHITE/BLACK (ordered by neighbor majority), recurses. On timeout → False. On leaf (`_uc == 0`) → `_ok()` verifies full connectivity.

### Propagation Rules

- **Rule 1 — 2×2 same-color** (`_p2` → `_set`): If any 2×2 block has 3 cells of the same color, the 4th is forced to the opposite color.
- **Rule 2 — 2×2 diagonal** (`_p2` → `_set`): If a 2×2 block has a diagonal pair of color C and one corner of color O, the last corner must be C.
- **Rule 3 — Perimeter contiguity** (`_perimeter`): On the outer boundary, same-color cells form contiguous arcs. If two cells of color C are on the perimeter with no opposite color on the arc between them, all unknowns on that arc are forced to C.
- **Rule 4 — Surrounded & single exit** (`_surrounded`, also in `_set`): (a) If an unknown cell has all known neighbors of the same color, set it to that color. (b) If a colored cell has exactly 1 unknown neighbor and all other known neighbors are the opposite color, that unknown must match the colored cell.
- **Rule 5 — 2×3/3×2 corner** (`_corner3`, also in `_set`): In a 2×3 (horizontal) or 3×2 (vertical) area, if the 4 corners have 3 of one color and 1 of the other color, the edge middle adjacent to the minority corner must be the minority color.
- **Bridge rule** (`_conn_expand`): Union-Find based. If a color has 2+ connected components and a component has exactly 1 unknown boundary cell, force that cell to the component's color. 0 boundary → conflict. Includes fast `_absorb()` to merge components after forcing.
- **Connectivity check** (`_ok`): Union-Find per color at leaf nodes. Also checks no 2×2 block is all same color.

### Incremental Propagation in `_set()`

`_set()` is the core assignment function. Every cell set triggers checks on:
- 4 surrounding 2×2 blocks (Rules 1 & 2 — conflict on diagonal same-color fill)
- 4 surrounding 2×3 horizontal blocks (Rule 5 edge middle)
- 4 surrounding 3×2 vertical blocks (Rule 5 edge middle)
- Surrounded checks (Rule 4) on the set cell and its unknown neighbors

Previously also ran `_bfs_comp()` per set — now commented out, replaced by `_conn_expand()` in the propagation loop.

### Union-Find `_conn_expand()` (Bridge Rule)

Single-pass UF building per-root unknown-neighbor sets (`au`). For each color with 2+ roots: if a root has 0 unknown neighbors → conflict; exactly 1 → force it via `_absorb()` (updates neighbor sets incrementally). `_absorb()` removes the cell from all neighbors' unknown sets and merges it into an adjacent same-color component.

### Cell Selection (`_pick`)

3-phase MRV heuristic:
- **Phase 1 — Bridge cells** (score ×5000): Unknown cells adjacent to multiple different components. Score includes component size weighting (smaller components prioritized).
- **Phase 2 — Single-component boundaries** (score ×100): Most constrained unknown on any component boundary.
- **Phase 3 — No components** (score ×1): Most constrained unknown cell (most colored neighbors).

### Task String RLE Format

Puzzles from the website use run-length encoding:
- Uppercase `W` = one white cell, `B` = one black cell
- Lowercase `a`-`z` = 1–26 consecutive unknown cells each

Example: `'BcBaBBWfWdWaWdBh'` decodes to a 6×6 grid with 9 given cells (5 black, 4 white).

`decode(task, N)` produces `list[list[int]]` for use by the solver. `encode(grid)` reverse-encodes a grid back to the RLE string format.

### Size Map (cn.puzzle-yin-yang.com)

`?size=N` parameter maps to puzzle dimensions:
- `0`/`1`/`2` → 6×6 (easy/normal/hard)
- `3`/`4`/`5` → 10×10
- `6`/`7`/`8` → 15×15
- `9`/`10`/`11` → 20×20
- `12`/`13`/`14` → 25×25
- `15` = 30×30 (daily), `16` = 35×35 (weekly), `17` = 40×40 (monthly)

CLI `--size` uses human keys (`6`, `10`, `15`, `20`, `25`, `30`, `35`, `40`) with optional difficulty suffix (`e`/`n`/`h`).

Also supports `daily`, `weekly`, `monthly` as size keys.

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

### Auto-save

Puzzles are automatically saved to `puzzles/` directory as JSON files when:
- Solver needs DFS to complete (tagged `dfs`)
- Solver times out / fails (when puzzle wasn't loaded from file)
- User passes `--save` flag

Saved format: `{"task": "<RLE>", "puzzleWidth": N, "puzzleHeight": N, "puzzleSize": "...", "puzzleId": "...", "puzzleDate": "..."}`

### CLI Puzzle Fetching

- `GET` requests for random/daily puzzles — parses `task`, `puzzleWidth`, `puzzleID`, and selected date from HTML
- `POST` requests for specific puzzle IDs — sends `specific=1&size=X&specid=Y` form data
- Headers include Chinese locale (`zh-CN,zh;q=0.9`) for compatibility

### Visualization

Terminal output uses ANSI escape codes:
- White background + black text (`○`) for WHITE cells
- Black background + white text (`●`) for BLACK cells
- Gray background (`·`) for UNKNOWN cells
- Column/row headers with bold formatting
- Verification status with ✓/✗ markers
