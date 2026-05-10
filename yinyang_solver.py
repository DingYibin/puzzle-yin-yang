"""
Yin-Yang Puzzle Solver
状态: 0=未知, 1=白色, 2=黑色
策略: DFS + 2×2 传播 + 桥规则 (连通分量边界检查)
"""
import time
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

    def load(self, grid):
        self.N = len(grid)
        self.g = [row[:] for row in grid]
        self.fixed = [[False]*self.N for _ in range(self.N)]
        for r in range(self.N):
            for c in range(self.N):
                if grid[r][c]:
                    self.fixed[r][c] = True

    # ---- undo ----
    def _set(self, r, c, v):
        if self.g[r][c] != v:
            self._st.append((r, c, self.g[r][c]))
            self.g[r][c] = v

    def _sn(self):
        return len(self._st)

    def _ba(self, n):
        while len(self._st) > n:
            r, c, v = self._st.pop()
            self.g[r][c] = v

    # ---- 2x2 propagation (rules 1 & 2) ----
    def _p2(self):
        """
        Rule 1: 2×2 block has 3 same → 4th must be opposite.
        Rule 2: 2×2 block has diagonal pair of C and one corner of O → last must be C.
        Returns True if any cell was changed, False if no changes.
        Returns None if a fully-filled 2×2 block has both diagonals same color (invalid).
        """
        changed = False
        while True:
            hit = False
            for r in range(self.N-1):
                for c in range(self.N-1):
                    cells = [(r,c),(r,c+1),(r+1,c),(r+1,c+1)]
                    vals = [self.g[x][y] for x,y in cells]

                    # Rule 1: 3 same → 4th opposite
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
                        changed = True
                        self._set(x, y, nv)
                        hit = True
                        continue

                    # Rule 2: diagonal pair of C + one corner O → last must be C
                    # Case 1: diagonal \ (v0==v3)
                    v0, v1, v2, v3 = vals
                    if v0 != self.UNKNOWN and v0 == v3:
                        if v1 != self.UNKNOWN and v1 != v0 and v2 == self.UNKNOWN:
                            changed = True
                            self._set(r+1, c, v0)
                            hit = True
                            continue
                        if v2 != self.UNKNOWN and v2 != v0 and v1 == self.UNKNOWN:
                            changed = True
                            self._set(r, c+1, v0)
                            hit = True
                            continue
                    # Case 2: diagonal / (v1==v2)
                    if v1 != self.UNKNOWN and v1 == v2:
                        if v0 != self.UNKNOWN and v0 != v1 and v3 == self.UNKNOWN:
                            changed = True
                            self._set(r+1, c+1, v1)
                            hit = True
                            continue
                        if v3 != self.UNKNOWN and v3 != v1 and v0 == self.UNKNOWN:
                            changed = True
                            self._set(r, c, v1)
                            hit = True
                            continue

                    # Validity: full 2×2 block with both diagonals same color is invalid
                    # Covers: all 4 same (e.g. W W / W W) and checkerboard (e.g. W B / B W)
                    if uk is None and v0 == v3 and v1 == v2:
                        return None

            if not hit:
                break
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

    def _bridge(self):
        """
        Bridge rule: component with 1 boundary → forced.
        Also check 0 boundary → conflict, and total_boundary < k-1 → impossible.
        """
        # Quick check: count components per color (stop at 2)
        def count_comps_fast(color, limit=2):
            cnt = 0
            visited = [[0]*self.N for _ in range(self.N)]
            # Use a different marker technique or just a simple queue
            for r in range(self.N):
                for c in range(self.N):
                    if self.g[r][c] == color and not visited[r][c]:
                        cnt += 1
                        if cnt >= limit:
                            return cnt
                        # BFS to mark this component
                        q = deque([(r, c)])
                        visited[r][c] = True
                        while q:
                            cr, cc = q.popleft()
                            for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                                nr, nc = cr+dr, cc+dc
                                if 0 <= nr < self.N and 0 <= nc < self.N and not visited[nr][nc] and self.g[nr][nc] == color:
                                    visited[nr][nc] = True
                                    q.append((nr, nc))
            return cnt

        w_cnt = count_comps_fast(self.WHITE)
        b_cnt = count_comps_fast(self.BLACK)

        if w_cnt <= 1 and b_cnt <= 1:
            return True

        for color in (self.WHITE, self.BLACK):
            comps = self._find_comps(color)
            k = len(comps)
            if k <= 1:
                continue
            total_b = 0
            for _, boundary in comps:
                b = len(boundary)
                total_b += b
                if b == 0:
                    return False
                if b == 1:
                    br, bc = next(iter(boundary))
                    if self.fixed[br][bc] and self.g[br][bc] != color:
                        return False
                    if self.g[br][bc] != color:
                        self._set(br, bc, color)
            if total_b < k - 1:
                return False
        return True

    def _conn_expand(self):
        """
        Connectivity expansion via Union-Find with per-root neighbor sets.

        Three sets per root node:
          aw — adjacent WHITE component roots
          ab — adjacent BLACK component roots
          au — adjacent UNKNOWN cell indices

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

        # Per-root neighbor sets
        aw = [set() for _ in range(S)]
        ab = [set() for _ in range(S)]
        au = [set() for _ in range(S)]

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
            # merge sets from child root to parent root
            if aw[ry]:
                aw[rx] |= aw[ry]
            if ab[ry]:
                ab[rx] |= ab[ry]
            if au[ry]:
                au[rx] |= au[ry]

        # Single pass: union + build neighbor sets simultaneously
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
                        else:
                            root, nroot = find(idx), find(nidx)
                            if v == 1:
                                ab[root].add(nroot)
                                aw[nroot].add(root)
                            else:
                                aw[root].add(nroot)
                                ab[nroot].add(root)
                    elif v and not nv:
                        root = find(idx)
                        au[root].add(nidx)
                        (aw if v == 2 else ab)[nidx].add(root)
                    elif not v and nv:
                        nroot = find(nidx)
                        au[nroot].add(idx)
                        (aw if nv == 2 else ab)[idx].add(nroot)
                    else:  # both unknown
                        au[idx].add(nidx)
                        au[nidx].add(idx)
                if r + 1 < N:
                    nv = g[r + 1][c]
                    nidx = (r + 1) * N + c
                    if v and nv:
                        if v == nv:
                            union(idx, nidx)
                        else:
                            root, nroot = find(idx), find(nidx)
                            if v == 1:
                                ab[root].add(nroot)
                                aw[nroot].add(root)
                            else:
                                aw[root].add(nroot)
                                ab[nroot].add(root)
                    elif v and not nv:
                        root = find(idx)
                        au[root].add(nidx)
                        (aw if v == 2 else ab)[nidx].add(root)
                    elif not v and nv:
                        nroot = find(nidx)
                        au[nroot].add(idx)
                        (aw if nv == 2 else ab)[idx].add(nroot)
                    else:  # both unknown
                        au[idx].add(nidx)
                        au[nidx].add(idx)

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

        # After setting a cell to a color, update UF and neighbor sets.
        # `roots` is the roots set for the color (white_roots or black_roots).
        def _absorb(cell, color, roots):
            r, c = divmod(cell, N)
            # Phase 1: remove cell from all neighbors' sets (it's no longer unknown)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < N and 0 <= nc < N:
                    nidx = nr * N + nc
                    if g[nr][nc] == 0:
                        au[nidx].discard(cell)
                        aw[nidx].discard(cell)
                        ab[nidx].discard(cell)
                    else:
                        nroot = find(nidx)
                        au[nroot].discard(cell)

            # Phase 2: establish new relationships.
            # Use union(nidx, cell) so nidx's root survives and cell is absorbed.
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < N and 0 <= nc < N):
                    continue
                nv = g[nr][nc]
                nidx = nr * N + nc
                if nv == 0:
                    my_root = find(cell)
                    au[my_root].add(nidx)
                    (aw if color == 2 else ab)[nidx].add(my_root)
                elif nv == color:
                    if find(nidx) != find(cell):
                        roots.discard(find(cell))
                        union(nidx, cell)  # nidx's root stays, cell merges in
                else:
                    my_root = find(cell)
                    nroot = find(nidx)
                    if color == 1:
                        ab[my_root].add(nroot)
                        aw[nroot].add(my_root)
                    else:
                        aw[my_root].add(nroot)
                        ab[nroot].add(my_root)

        for roots, color in ((white_roots, 1), (black_roots, 2)):
            if len(roots) >= 2:
                for root in list(roots):
                    if find(root) != root:
                        roots.discard(root)
                        continue
                    b = len(au[root])
                    if b == 0:
                        return None
                    if b == 1:
                        cell = next(iter(au[root]))
                        ur, uc = divmod(cell, N)
                        if g[ur][uc] != color:
                            self._set(ur, uc, color)
                            _absorb(cell, color, roots)
                            changed = True
                            if len(roots) < 2:
                                break

        return changed

    def _propagate(self, verbose=False):
        """Apply deduction rules until stable (p2 + surrounded + corner3 + perimeter + conn_expand)."""
        while True:
            c1 = self._p2()
            if c1 is None:
                return False
            c2 = self._surrounded()
            c3 = self._corner3()
            c4 = self._perimeter()
            c5 = self._conn_expand()
            if c5 is None:
                return False
            if verbose and (c1 or c2 or c3 or c4 or c5):
                self.pc()
            if not c1 and not c2 and not c3 and not c4 and not c5:
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
                        self._set(r, c, color)
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
                        self._set(ur, uc, v)
                        changed = True
        return changed

    # ---- 2x3 / 3x2 corner rule (rule 5) ----
    def _corner3(self):
        """
        Rule 5: in a 2×3 or 3×2 area, if 4 corners are colored with 3 of
        one color and 1 of the other, the middle cell adjacent to the
        minority corner must also be the minority color.
        Returns True if any cell was changed, False otherwise.
        """
        changed = False
        N = self.N
        g = self.g

        # 2×3 horizontal: (r,c) to (r+1,c+2)
        for r in range(N - 1):
            for c in range(N - 2):
                corners = [(r,c), (r,c+2), (r+1,c), (r+1,c+2)]
                vals = [g[x][y] for x,y in corners]
                if any(v == self.UNKNOWN for v in vals):
                    continue
                wc = sum(1 for v in vals if v == self.WHITE)
                bc = sum(1 for v in vals if v == self.BLACK)
                if wc == 3 and bc == 1:
                    for (cr, cc), v in zip(corners, vals):
                        if v == self.BLACK and g[cr][c+1] == self.UNKNOWN:
                            self._set(cr, c+1, self.BLACK)
                            changed = True
                            break
                elif bc == 3 and wc == 1:
                    for (cr, cc), v in zip(corners, vals):
                        if v == self.WHITE and g[cr][c+1] == self.UNKNOWN:
                            self._set(cr, c+1, self.WHITE)
                            changed = True
                            break

        # 3×2 vertical: (r,c) to (r+2,c+1)
        for r in range(N - 2):
            for c in range(N - 1):
                corners = [(r,c), (r+2,c), (r,c+1), (r+2,c+1)]
                vals = [g[x][y] for x,y in corners]
                if any(v == self.UNKNOWN for v in vals):
                    continue
                wc = sum(1 for v in vals if v == self.WHITE)
                bc = sum(1 for v in vals if v == self.BLACK)
                if wc == 3 and bc == 1:
                    for (cr, cc), v in zip(corners, vals):
                        if v == self.BLACK and g[r+1][cc] == self.UNKNOWN:
                            self._set(r+1, cc, self.BLACK)
                            changed = True
                            break
                elif bc == 3 and wc == 1:
                    for (cr, cc), v in zip(corners, vals):
                        if v == self.WHITE and g[r+1][cc] == self.UNKNOWN:
                            self._set(r+1, cc, self.WHITE)
                            changed = True
                            break

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
                        self._set(peri[a][0], peri[a][1], color)
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
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] == self.UNKNOWN:
                    return False
        return True

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
    def solve(self):
        self.t0 = time.time()
        self.nodes = 0
        self._st = []
        if not self._propagate(verbose=self.verbose):
            return False
        if self._done():
            return self._ok()
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
            if self._propagate() and self._dfs():
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
        print("=" * 50)


def decode(t: str, n: int):
    c = []
    for ch in t:
        if ch == 'W': c.append(1)
        elif ch == 'B': c.append(2)
        elif 'a' <= ch <= 'z': c.extend([0]*(ord(ch)-ord('a')+1))
    return [c[r*n:(r+1)*n] for r in range(n)]


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
