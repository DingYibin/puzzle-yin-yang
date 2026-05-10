"""
Yin-Yang Puzzle Solver
状态: 0=未知, 1=白色, 2=黑色
策略: DFS + 2×2 传播 + 桥规则 (连通分量边界检查)
"""
import time
import json
import os
from datetime import datetime
from collections import deque


class Solver:
    UNKNOWN, WHITE, BLACK = 0, 1, 2

    def __init__(self, time_limit=5.0, verbose=False):
        self.tlim = time_limit
        self.verbose = verbose
        self.N = 0
        self.g = []       # grid
        self.fixed = []    # given cells
        self.nodes = 0
        self.t0 = 0
        self._st = []     # undo stack
        self._timing = {}
        self._prop_iterations = 0
        self._wc = self._bc = self._uc = 0

    def load(self, grid):
        self.N = len(grid)
        self.g = [row[:] for row in grid]
        self.fixed = [[False]*self.N for _ in range(self.N)]
        self._wc = self._bc = self._uc = 0
        for r in range(self.N):
            for c in range(self.N):
                v = grid[r][c]
                if v == self.WHITE:
                    self._wc += 1
                elif v == self.BLACK:
                    self._bc += 1
                else:
                    self._uc += 1
                if v:
                    self.fixed[r][c] = True

    # ---- undo & incremental 2x2 ----
    def _set(self, r, c, v):
        """
        Set cell (r,c) to v, then check the 4 surrounding 2×2 blocks
        and 8 surrounding 2×3/3×2 blocks.
        If a block has 3 of one color + 1 unknown → set the unknown.
        If a filled 2×2 has both diagonals the same → conflict → return False.
        Returns True if valid, False if conflict.
        """
        old = self.g[r][c]
        if old == v:
            return True
        self._st.append((r, c, old))
        # update counts
        if old == 0: self._uc -= 1
        elif old == 1: self._wc -= 1
        else: self._bc -= 1
        if v == 0: self._uc += 1
        elif v == 1: self._wc += 1
        else: self._bc += 1
        self.g[r][c] = v

        N, g = self.N, self.g

        # ---- 2×2 checks (4 blocks) ----
        for dr in (-1, 0):
            for dc in (-1, 0):
                tr, tc = r + dr, c + dc  # top-left corner of 2×2 block
                if not (0 <= tr <= N - 2 and 0 <= tc <= N - 2):
                    continue
                cells = [(tr, tc), (tr, tc + 1), (tr + 1, tc), (tr + 1, tc + 1)]
                vv = [g[x][y] for x, y in cells]

                # All filled + invalid diagonal → conflict
                if all(v != 0 for v in vv) and vv[0] == vv[3] and vv[1] == vv[2]:
                    return False

                uk = None
                wc = bc = 0
                for i, val in enumerate(vv):
                    if val == 0:
                        uk = i
                    elif val == 1:
                        wc += 1
                    else:
                        bc += 1

                # Rule 1: 3 same → 4th opposite
                if uk is not None and (wc == 3 or bc == 3):
                    uv, ux, uy = (2, *cells[uk]) if wc == 3 else (1, *cells[uk])
                    if not self._set(ux, uy, uv):
                        return False
                    continue

                # Rule 2: diagonal pair of C + one corner O → last must be C
                v0, v1, v2, v3 = vv
                if v0 != 0 and v0 == v3:
                    if v1 != 0 and v1 != v0 and v2 == 0:
                        if not self._set(cells[2][0], cells[2][1], v0):
                            return False
                        continue
                    if v2 != 0 and v2 != v0 and v1 == 0:
                        if not self._set(cells[1][0], cells[1][1], v0):
                            return False
                        continue
                if v1 != 0 and v1 == v2:
                    if v0 != 0 and v0 != v1 and v3 == 0:
                        if not self._set(cells[3][0], cells[3][1], v1):
                            return False
                        continue
                    if v3 != 0 and v3 != v1 and v0 == 0:
                        if not self._set(cells[0][0], cells[0][1], v1):
                            return False
                        continue

        # ---- 2×3 horizontal checks (4 blocks where (r,c) is a corner) ----
        for dr in (-1, 0):
            for dc in (-2, 0):
                tr, tc = r + dr, c + dc
                if not (0 <= tr <= N - 2 and 0 <= tc <= N - 3):
                    continue
                corners = [(tr, tc), (tr, tc + 2), (tr + 1, tc), (tr + 1, tc + 2)]
                cv = [g[x][y] for x, y in corners]
                if any(v == 0 for v in cv):
                    continue
                wc = sum(1 for v in cv if v == 1)
                bc = sum(1 for v in cv if v == 2)
                if wc == 3 and bc == 1:
                    for (cr, _), val in zip(corners, cv):
                        if val == 2 and g[cr][tc + 1] == 0:
                            if not self._set(cr, tc + 1, 2):
                                return False
                            break
                elif bc == 3 and wc == 1:
                    for (cr, _), val in zip(corners, cv):
                        if val == 1 and g[cr][tc + 1] == 0:
                            if not self._set(cr, tc + 1, 1):
                                return False
                            break

        # ---- 3×2 vertical checks (4 blocks where (r,c) is a corner) ----
        for dr in (-2, 0):
            for dc in (-1, 0):
                tr, tc = r + dr, c + dc
                if not (0 <= tr <= N - 3 and 0 <= tc <= N - 2):
                    continue
                corners = [(tr, tc), (tr + 2, tc), (tr, tc + 1), (tr + 2, tc + 1)]
                cv = [g[x][y] for x, y in corners]
                if any(v == 0 for v in cv):
                    continue
                wc = sum(1 for v in cv if v == 1)
                bc = sum(1 for v in cv if v == 2)
                if wc == 3 and bc == 1:
                    for (_, cc), val in zip(corners, cv):
                        if val == 2 and g[tr + 1][cc] == 0:
                            if not self._set(tr + 1, cc, 2):
                                return False
                            break
                elif bc == 3 and wc == 1:
                    for (_, cc), val in zip(corners, cv):
                        if val == 1 and g[tr + 1][cc] == 0:
                            if not self._set(tr + 1, cc, 1):
                                return False
                            break

        # ---- surrounded checks ----
        # Case 1: UNKNOWN neighbor — all known neighbors same color?
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < N and 0 <= nc < N) or g[nr][nc] != 0:
                continue
            color = None
            ok = True
            for ddr, ddc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nnr, nnc = nr + ddr, nc + ddc
                if 0 <= nnr < N and 0 <= nnc < N:
                    nnv = g[nnr][nnc]
                    if nnv == 0:
                        ok = False
                        break
                    if color is None:
                        color = nnv
                    elif nnv != color:
                        ok = False
                        break
            if ok and color is not None:
                if not self._set(nr, nc, color):
                    return False

        # Case 2: (r,c) and its colored neighbors — exactly 1 unknown, rest opposite?
        for cr, cc in [(r, c)] + [(r + dr, c + dc) for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)) if 0 <= r+dr < N and 0 <= c+dc < N and g[r+dr][c+dc] != 0]:
            cv2 = g[cr][cc]
            opp2 = 2 if cv2 == 1 else 1
            unk_pos = None
            valid = True
            for dr2, dc2 in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nnr, nnc = cr + dr2, cc + dc2
                if 0 <= nnr < N and 0 <= nnc < N:
                    nnv = g[nnr][nnc]
                    if nnv == 0:
                        if unk_pos is None:
                            unk_pos = (nnr, nnc)
                        else:
                            valid = False
                            break
                    elif nnv != opp2:
                        valid = False
                        break
            if valid and unk_pos is not None:
                ur, uc = unk_pos
                if not self._set(ur, uc, cv2):
                    return False

        return True

    def _sn(self):
        return len(self._st)

    def _ba(self, n):
        while len(self._st) > n:
            r, c, old = self._st.pop()
            cur = self.g[r][c]
            if cur == 0: self._uc -= 1
            elif cur == 1: self._wc -= 1
            else: self._bc -= 1
            if old == 0: self._uc += 1
            elif old == 1: self._wc += 1
            else: self._bc += 1
            self.g[r][c] = old

    # ---- 2x2 preprocessing (rules 1 & 2) ----
    def _p2(self):
        """
        Full-grid 2×2 deduction scan (runs once during preprocessing).
        Rule 1: 2×2 block has 3 same → 4th must be opposite.
        Rule 2: 2×2 block has diagonal pair of C and one corner of O → last must be C.
        After this, _set handles all incremental 2×2 propagation.
        Returns True if any cell was changed.
        """
        changed = False
        for r in range(self.N - 1):
            for c in range(self.N - 1):
                cells = [(r,c),(r,c+1),(r+1,c),(r+1,c+1)]
                vals = [self.g[x][y] for x,y in cells]

                uk = None
                wc = bc = 0
                for i, v in enumerate(vals):
                    if v == self.UNKNOWN:
                        uk = i
                    elif v == self.WHITE:
                        wc += 1
                    elif v == self.BLACK:
                        bc += 1

                if uk is not None and (wc == 3 or bc == 3):
                    x, y = cells[uk]
                    nv = self.BLACK if wc == 3 else self.WHITE
                    self._set(x, y, nv)
                    changed = True
                    continue

                v0, v1, v2, v3 = vals
                if v0 != self.UNKNOWN and v0 == v3:
                    if v1 != self.UNKNOWN and v1 != v0 and v2 == self.UNKNOWN:
                        self._set(r + 1, c, v0)
                        changed = True
                        continue
                    if v2 != self.UNKNOWN and v2 != v0 and v1 == self.UNKNOWN:
                        self._set(r, c + 1, v0)
                        changed = True
                        continue
                if v1 != self.UNKNOWN and v1 == v2:
                    if v0 != self.UNKNOWN and v0 != v1 and v3 == self.UNKNOWN:
                        self._set(r + 1, c + 1, v1)
                        changed = True
                        continue
                    if v3 != self.UNKNOWN and v3 != v1 and v0 == self.UNKNOWN:
                        self._set(r, c, v1)
                        changed = True
                        continue
        return changed

    # ---- component analysis & bridge rule ----
    def _find_comps(self, color):
        """return [(cell_count, boundary_set)]"""
        res = []
        visited = [[0]*self.N for _ in range(self.N)]
        vmark = 0
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] == color and not visited[r][c]:
                    vmark += 1
                    mk = vmark
                    boundary = set()
                    q = deque([(r,c)])
                    visited[r][c] = mk
                    cells = 0
                    while q:
                        cr, cc = q.popleft()
                        cells += 1
                        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < self.N and 0 <= nc < self.N:
                                if self.g[nr][nc] == color and visited[nr][nc] != mk:
                                    visited[nr][nc] = mk
                                    q.append((nr, nc))
                                elif self.g[nr][nc] == self.UNKNOWN:
                                    boundary.add((nr, nc))
                    res.append((cells, boundary))  # noqa: F841
        return res

    def _conn_expand(self):
        """
        Connectivity expansion via Union-Find with per-root unknown-neighbor sets.

        au — adjacent UNKNOWN cell indices per root

        If a color has 2+ components and one component has exactly 1 unknown
        boundary cell, force that cell to the component's color.
        Returns True if any cell was changed, False if no changes.
        Returns None if a color has 2+ components but one has 0 unknown
        boundary cells (impossible to connect, current state is invalid).
        """
        N = self.N
        g = self.g
        S = N * N
        parent = list(range(S))

        # Per-root unknown neighbor sets (lazy: None until first add)
        au = [None] * S

        def ensure(arr, idx):
            if arr[idx] is None:
                arr[idx] = set()
            return arr[idx]

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry:
                return
            parent[ry] = rx
            if au[ry] is not None:
                if au[rx] is None:
                    au[rx] = au[ry]
                else:
                    au[rx] |= au[ry]
                au[ry] = None

        # Single pass: union + build unknown neighbor sets
        for r in range(N):
            for c in range(N):
                v = g[r][c]
                idx = r * N + c
                if c + 1 < N:
                    nv = g[r][c + 1]
                    nidx = r * N + c + 1
                    if v and nv:
                        if v == nv:
                            union(idx, nidx)
                    elif v and not nv:
                        root = find(idx)
                        ensure(au, root).add(nidx)
                    elif not v and nv:
                        nroot = find(nidx)
                        ensure(au, nroot).add(idx)
                    else:  # both unknown
                        ensure(au, idx).add(nidx)
                        ensure(au, nidx).add(idx)
                if r + 1 < N:
                    nv = g[r + 1][c]
                    nidx = (r + 1) * N + c
                    if v and nv:
                        if v == nv:
                            union(idx, nidx)
                    elif v and not nv:
                        root = find(idx)
                        ensure(au, root).add(nidx)
                    elif not v and nv:
                        nroot = find(nidx)
                        ensure(au, nroot).add(idx)
                    else:  # both unknown
                        ensure(au, idx).add(nidx)
                        ensure(au, nidx).add(idx)

        # Collect roots per color
        white_roots = set()
        black_roots = set()
        for r in range(N):
            for c in range(N):
                v = g[r][c]
                if v == 1:
                    white_roots.add(find(r * N + c))
                elif v == 2:
                    black_roots.add(find(r * N + c))

        changed = False

        def _absorb(cell, color, roots):
            r, c = divmod(cell, N)
            # Remove cell from all neighbors' unknown sets
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < N and 0 <= nc < N:
                    nidx = nr * N + nc
                    if g[nr][nc] == 0:
                        if au[nidx] is not None:
                            au[nidx].discard(cell)
                    else:
                        nroot = find(nidx)
                        if au[nroot] is not None:
                            au[nroot].discard(cell)
            # Add new unknown neighbors from this cell
            my_root = find(cell)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < N and 0 <= nc < N):
                    continue
                if g[nr][nc] == 0:
                    ensure(au, my_root).add(nr * N + nc)
                elif g[nr][nc] == color:
                    if find(nr * N + nc) != my_root:
                        roots.discard(my_root)
                        union(nr * N + nc, cell)

        for roots, color in ((white_roots, 1), (black_roots, 2)):
            if len(roots) >= 2:
                for root in list(roots):
                    if find(root) != root:
                        roots.discard(root)
                        continue
                    b = len(au[root]) if au[root] else 0
                    if b == 0:
                        return None
                    if b == 1:
                        cell = next(iter(au[root]))
                        ur, uc = divmod(cell, N)
                        if g[ur][uc] != color:
                            if not self._set(ur, uc, color):
                                return None
                            _absorb(cell, color, roots)
                            changed = True
                            if len(roots) < 2:
                                break

        return changed

    def _try_both(self):
        """
        For each unknown cell, try both colors with full propagation.
        If exactly one color is viable, force it.
        If both conflict, the puzzle is unsolvable → return False.
        If both OK, skip and continue.
        Returns True if any cell was changed, False otherwise.
        """
        changed = False
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] != self.UNKNOWN:
                    continue
                sp = self._sn()
                self._set(r, c, self.WHITE)
                ok_w = self._propagate()
                self._ba(sp)

                sp = self._sn()
                self._set(r, c, self.BLACK)
                ok_b = self._propagate()
                self._ba(sp)

                if ok_w and not ok_b:
                    self._set(r, c, self.WHITE)
                    self._propagate()
                    changed = True
                    if self.verbose:
                        print(f"[try_both] force ({r},{c}) = WHITE")
                        self.pc()
                elif not ok_w and ok_b:
                    self._set(r, c, self.BLACK)
                    self._propagate()
                    changed = True
                    if self.verbose:
                        print(f"[try_both] force ({r},{c}) = BLACK")
                        self.pc()
                elif not ok_w and not ok_b:
                    return False
                # both OK → skip
        return changed

    def _propagate(self):
        """
        Apply deduction rules until stable.
        (perimeter + conn_expand; all other rules handled by _set incrementally)
        """
        while True:
            self._prop_iterations += 1
            t0 = time.time()
            c1 = self._perimeter()
            self._timing['_perimeter'] = self._timing.get('_perimeter', 0) + time.time() - t0
            if c1 is None:
                return False
            t0 = time.time()
            c2 = self._conn_expand()
            self._timing['_conn_expand'] = self._timing.get('_conn_expand', 0) + time.time() - t0
            if c2 is None:
                return False
            if not c1 and not c2:
                break
        return True

    # ---- surrounded & single unknown neighbor (rule 4) ----
    def _surrounded(self):
        """
        Two cases:
        1. UNKNOWN cell: all neighbors known and same color → set cell.
        2. COLORED cell: exactly 1 unknown neighbor, all other known
           neighbors opposite → set that unknown neighbor.
        """
        changed = False
        for r in range(self.N):
            for c in range(self.N):
                v = self.g[r][c]
                if v == self.UNKNOWN:
                    # Case 1: unknown cell, check if all neighbors agree
                    color = None
                    ok = True
                    for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < self.N and 0 <= nc < self.N:
                            nv = self.g[nr][nc]
                            if nv == self.UNKNOWN:
                                ok = False
                                break
                            if color is None:
                                color = nv
                            elif nv != color:
                                ok = False
                                break
                    if ok and color is not None:
                        if not self._set(r, c, color):
                            return None
                        changed = True
                else:
                    # Case 2: colored cell, check for single unknown exit
                    opp = self.WHITE if v == self.BLACK else self.BLACK
                    unk_pos = None
                    for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                        nr, nc = r+dr, c+dc
                        if 0 <= nr < self.N and 0 <= nc < self.N:
                            nv = self.g[nr][nc]
                            if nv == self.UNKNOWN:
                                if unk_pos is None:
                                    unk_pos = (nr, nc)
                                else:
                                    unk_pos = None
                                    break
                            elif nv != opp:
                                unk_pos = None
                                break
                    if unk_pos is not None:
                        ur, uc = unk_pos
                        if not self._set(ur, uc, v):
                            return None
                        changed = True
        return changed

    # ---- 2x3 / 3x2 corner rule (rule 5) ----
    def _corner3_h(self, r, c):
        """Horizontal 2×3 check: (r,c) to (r+1,c+2) → middle at (cr, c+1)"""
        N, g = self.N, self.g
        if c + 2 >= N:
            return False
        corners = [(r,c), (r,c+2), (r+1,c), (r+1,c+2)]
        vals = [g[x][y] for x,y in corners]
        if any(v == self.UNKNOWN for v in vals):
            return False
        wc = sum(1 for v in vals if v == self.WHITE)
        bc = sum(1 for v in vals if v == self.BLACK)
        if wc == 3 and bc == 1:
            for (cr, _), v in zip(corners, vals):
                if v == self.BLACK and g[cr][c+1] == self.UNKNOWN:
                    if not self._set(cr, c+1, self.BLACK):
                        return None
                    return True
        elif bc == 3 and wc == 1:
            for (cr, _), v in zip(corners, vals):
                if v == self.WHITE and g[cr][c+1] == self.UNKNOWN:
                    if not self._set(cr, c+1, self.WHITE):
                        return None
                    return True
        return False

    def _corner3_v(self, r, c):
        """Vertical 3×2 check: (r,c) to (r+2,c+1) → middle at (r+1, cc)"""
        N, g = self.N, self.g
        if r + 2 >= N:
            return False
        corners = [(r,c), (r+2,c), (r,c+1), (r+2,c+1)]
        vals = [g[x][y] for x,y in corners]
        if any(v == self.UNKNOWN for v in vals):
            return False
        wc = sum(1 for v in vals if v == self.WHITE)
        bc = sum(1 for v in vals if v == self.BLACK)
        if wc == 3 and bc == 1:
            for (_, cc), v in zip(corners, vals):
                if v == self.BLACK and g[r+1][cc] == self.UNKNOWN:
                    if not self._set(r+1, cc, self.BLACK):
                        return None
                    return True
        elif bc == 3 and wc == 1:
            for (_, cc), v in zip(corners, vals):
                if v == self.WHITE and g[r+1][cc] == self.UNKNOWN:
                    if not self._set(r+1, cc, self.WHITE):
                        return None
                    return True
        return False

    def _corner3(self):
        """
        Rule 5: in a 2×3 or 3×2 area, if 4 corners are colored with 3 of
        one color and 1 of the other, the middle cell adjacent to the
        minority corner must also be the minority color.
        Returns True if any cell was changed, False otherwise.
        Returns None if conflict detected.
        """
        changed = False
        N = self.N
        for r in range(N - 1):
            for c in range(N - 1):
                rv = self._corner3_h(r, c)
                if rv is None:
                    return None
                if rv:
                    changed = True
                rv = self._corner3_v(r, c)
                if rv is None:
                    return None
                if rv:
                    changed = True
        return changed

    def _perimeter(self):
        """
        Rule 3: on the perimeter, if both colors appear and one color has
        2+ cells, connect those cells along the perimeter arc that does
        not pass through the opposite color. Returns True if changed.
        """
        changed = False
        N = self.N
        if N <= 2:
            return changed

        # Perimeter in clockwise order
        peri = (
            [(0, c) for c in range(N)] +
            [(r, N-1) for r in range(1, N)] +
            [(N-1, c) for c in range(N-2, -1, -1)] +
            [(r, 0) for r in range(N-2, 0, -1)]
        )
        P = len(peri)
        # Keep only colored cells with their perimeter indices
        colored = [(i, self.g[r][c]) for i, (r, c) in enumerate(peri)
                   if self.g[r][c] != self.UNKNOWN]

        # Need both colors present
        has = {v for _, v in colored}
        if self.WHITE not in has or self.BLACK not in has:
            return changed

        for color in (self.WHITE, self.BLACK):
            opp = self.BLACK if color == self.WHITE else self.WHITE
            idxs = [i for i, v in colored if v == color]
            if len(idxs) < 2:
                continue

            for k in range(len(idxs)):
                i = idxs[k]
                j = idxs[(k + 1) % len(idxs)]
                if i < j:
                    arc = list(range(i + 1, j))
                else:
                    arc = list(range(i + 1, P)) + list(range(0, j))
                if not arc:
                    continue
                # Skip if opposite color blocks this arc
                if any(self.g[peri[a][0]][peri[a][1]] == opp for a in arc):
                    continue
                # Fill unknowns on this arc
                for a in arc:
                    if self.g[peri[a][0]][peri[a][1]] == self.UNKNOWN:
                        if not self._set(peri[a][0], peri[a][1], color):
                            return None
                        changed = True

        return changed

    # ---- connectivity check (union-find) ----
    def _ok(self):
        """
        Check connectivity via Union-Find: adjacent same-color cells are merged.
        Both colors must each form at most 1 connected component.
        """
        N = self.N
        parent = list(range(N * N))
        rank = [0] * (N * N)

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry:
                return
            if rank[rx] < rank[ry]:
                parent[rx] = ry
            elif rank[rx] > rank[ry]:
                parent[ry] = rx
            else:
                parent[ry] = rx
                rank[rx] += 1

        for r in range(N):
            for c in range(N):
                v = self.g[r][c]
                if v == self.UNKNOWN:
                    continue
                idx = r * N + c
                if c + 1 < N and self.g[r][c + 1] == v:
                    union(idx, r * N + c + 1)
                if r + 1 < N and self.g[r + 1][c] == v:
                    union(idx, (r + 1) * N + c)

        white_roots = set()
        black_roots = set()
        for r in range(N):
            for c in range(N):
                v = self.g[r][c]
                if v == self.UNKNOWN:
                    continue
                root = find(r * N + c)
                if v == self.WHITE:
                    white_roots.add(root)
                else:
                    black_roots.add(root)

        if len(white_roots) > 1 or len(black_roots) > 1:
            return False

        # Also check no 2×2 block is all same color
        for r in range(N - 1):
            for c in range(N - 1):
                v = self.g[r][c]
                if v != self.UNKNOWN and all(self.g[r + dr][c + dc] == v
                                              for dr in (0, 1) for dc in (0, 1)):
                    return False
        return True

    def _done(self):
        return self._uc == 0

    # ---- cell selection ----
    def _pick(self):
        """
        Pick from smallest multi-component boundary; prefer cells that
        are adjacent to multiple different components (bridge cells).
        """
        # Precompute all components for both colors
        w_comps = self._find_comps(self.WHITE)
        b_comps = self._find_comps(self.BLACK)

        best, best_sc = None, -1

        # Phase 1: multi-component colors — bridge score
        for _, comps in ((self.WHITE, w_comps), (self.BLACK, b_comps)):
            if len(comps) < 2:
                continue
            # Map unknown cells to component sets they border
            cell_to_comps = {}
            for ci, (_, boundary) in enumerate(comps):
                for br, bc in boundary:
                    cell_to_comps.setdefault((br, bc), set()).add(ci)

            for (br, bc), comp_set in cell_to_comps.items():
                n_comps = len(comp_set)
                sc = n_comps * 5000
                for ci in comp_set:
                    sc += 2000 - min(len(comps[ci][1]), 10) * 100
                if sc > best_sc:
                    best_sc = sc
                    best = (br, bc)

        if best:
            return best

        # Phase 2: single-component colors — most constrained boundary
        for comps in (w_comps, b_comps):
            for _, boundary in comps:
                for br, bc in boundary:
                    sc = sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                            if 0 <= br+dr < self.N and 0 <= bc+dc < self.N and self.g[br+dr][bc+dc])
                    sc = sc * 100
                    if sc > best_sc:
                        best_sc = sc
                        best = (br, bc)

        if best:
            return best

        # Phase 3: no components at all — most constrained unknown
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] == self.UNKNOWN:
                    sc = sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                            if 0 <= r+dr < self.N and 0 <= c+dc < self.N)
                    if sc > best_sc:
                        best_sc = sc
                        best = (r, c)
        return best

    # ---- DFS ----
    def solve(self, save_on_fail=False):
        self.t0 = time.time()
        self.nodes = 0
        self._st = []
        self._timing = {}
        self._prop_iterations = 0
        self._initial_grid = [row[:] for row in self.g]
        # Preprocessing: full-grid 2×2 & corner3 deduction
        # (after this, _set handles both incrementally)
        self._p2()
        self._corner3()
        self._surrounded()
        self._conn_expand()
        if self._done():
            return True
        if not self._propagate():
            return False
        if self._done():
            return True
        # Try-both: before DFS, try each unknown with both colors.
        # If one color causes conflict, the other is forced.
        if self.verbose:
            print(f"\n── Try-Both Round 0 ──")
            self.pc()
        _try_round = 0
        while True:
            _try_round += 1
            tb = self._try_both()
            if not tb:
                break
            if self.verbose:
                print(f"\n── Try-Both Round {_try_round} ──")
                self.pc()
            if not self._propagate():
                return False
            if self._done():
                return True
        if save_on_fail:
            if self.verbose:
                print("Try-both 无法完成求解，自动保存谜题...")
            self._save_puzzle(self._initial_grid, tag="dfs")
        return self._dfs()

    def _dfs(self):
        if time.time() - self.t0 > self.tlim:
            return False
        self.nodes += 1
        cell = self._pick()
        if cell is None:
            return self._ok()
        r, c = cell
        # forbid colors creating 2x2
        wok = bok = True
        for dr in (-1, 0):
            for dc in (-1, 0):
                cr, cc = r+dr, c+dc
                if 0 <= cr < self.N-1 and 0 <= cc < self.N-1:
                    o = [(x,y) for x,y in [(cr,cc),(cr,cc+1),(cr+1,cc),(cr+1,cc+1)] if (x,y) != (r,c)]
                    if all(self.g[x][y] == self.WHITE for x,y in o): wok = False
                    if all(self.g[x][y] == self.BLACK for x,y in o): bok = False
        wc = bc = 0
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.N and 0 <= nc < self.N:
                if self.g[nr][nc] == self.WHITE: wc += 1
                elif self.g[nr][nc] == self.BLACK: bc += 1
        order = []
        if wok and bok:
            order = [self.WHITE, self.BLACK] if wc >= bc else [self.BLACK, self.WHITE]
        elif wok: order = [self.WHITE]
        elif bok: order = [self.BLACK]
        else: return False
        for co in order:
            sp = self._sn()
            self._set(r, c, co)
            if self._propagate():
                if self.verbose:
                    print(f"[DFS] node {self.nodes}: try ({r},{c}) = {'WHITE' if co == 1 else 'BLACK'}")
                    self.pc()
                if self._dfs():
                    return True
            self._ba(sp)
        return False

    # ---- print ----
    def pc(self):
        WB = "\033[47m\033[30m"; BB = "\033[40m\033[97m"; GB = "\033[100m\033[97m"; RE = "\033[0m"; BO = "\033[1m"
        cw = 3
        print("   " + "".join(f"{BO}{c:^{cw}}{RE}" for c in range(self.N)))
        print("   " + "─" * (cw * self.N))
        for r in range(self.N):
            s = f"{BO}{r:2}{RE}│"
            for c in range(self.N):
                v = self.g[r][c]
                if v == self.WHITE: s += f"{WB} ○ {RE}"
                elif v == self.BLACK: s += f"{BB} ● {RE}"
                else: s += f"{GB} · {RE}"
            print(s)
        print("   " + "─" * (cw * self.N))

    def ps(self):
        RE = "\033[0m"; BO = "\033[1m"
        print(f"\n{BO}结果{RE}")
        print("=" * 50)
        self.pc()
        wc = sum(1 for r in range(self.N) for c in range(self.N) if self.g[r][c]==self.WHITE)
        bc = sum(1 for r in range(self.N) for c in range(self.N) if self.g[r][c]==self.BLACK)
        print(f"○白={wc} ●黑={bc} 总={self.N*self.N}")
        ok = self._ok()
        print(f"验证: {'✓' if ok else '✗'}")
        print(f"时间={time.time()-self.t0:.3f}s 节点={self.nodes}")
        if self.verbose and self._timing:
            print(f"  propagate 迭代: {self._prop_iterations}")
            print(f"  规则耗时:")
            for rule in ['_perimeter', '_conn_expand']:
                t = self._timing.get(rule, 0)
                print(f"    {rule:20s} {t*1000:9.3f} ms")
        print("=" * 50)

    def _save_puzzle(self, grid, tag=""):
        """Save puzzle to puzzles/<timestamp>.json when try_both cannot fully solve."""
        task = encode(grid)
        w = len(grid)
        h = len(grid[0]) if grid else w
        data = {"task": task, "puzzleWidth": w, "puzzleHeight": h}
        if hasattr(self, '_puzzle_meta'):
            data.update(self._puzzle_meta)
        tag_suffix = f"_{tag}" if tag else ""
        filename = f"puzzle-yin-yang{tag_suffix}_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        os.makedirs("puzzles", exist_ok=True)
        filepath = os.path.join("puzzles", filename)
        with open(filepath, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if self.verbose:
            print(f"谜题已保存到 {filepath}")


def decode(t: str, n: int):
    c = []
    for ch in t:
        if ch == 'W': c.append(1)
        elif ch == 'B': c.append(2)
        elif 'a' <= ch <= 'z': c.extend([0]*(ord(ch)-ord('a')+1))
    return [c[r*n:(r+1)*n] for r in range(n)]


def encode(grid: list[list[int]]) -> str:
    """Encode grid back to task string RLE format."""
    N = len(grid)
    flat = [grid[r][c] for r in range(N) for c in range(N)]
    result = []
    i = 0
    while i < len(flat):
        v = flat[i]
        if v == 1:
            result.append('W')
            i += 1
        elif v == 2:
            result.append('B')
            i += 1
        else:
            j = i
            while j < len(flat) and flat[j] == 0:
                j += 1
            count = j - i
            while count > 0:
                chunk = min(count, 26)
                result.append(chr(ord('a') + chunk - 1))
                count -= chunk
            i = j
    return ''.join(result)


def solve(grid, tl=5.0, vb=True):
    s = Solver(time_limit=tl, verbose=vb)
    s.load(grid)
    if vb:
        print(f"\n{s.N}x{s.N}")
        s.pc()
    ok = s.solve()
    if ok and vb: s.ps()
    elif not ok and vb: print(f"\n❌ ({s.nodes} nodes)")
    return ok, s
