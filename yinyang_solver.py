"""
Yin-Yang Puzzle Solver
State: 0=UNKNOWN, 1=WHITE, 2=BLACK
Strategy: DFS + 2×2 propagation + bridge rule (connectivity boundary check)
"""
import time
from collections import deque


def _timeit(key):
    """Decorator that accumulates method execution time in self._timing[key]."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            _t0 = time.time()
            try:
                return func(self, *args, **kwargs)
            finally:
                self._timing[key] = self._timing.get(key, 0.0) + time.time() - _t0
        return wrapper
    return decorator


class Solver:
    UNKNOWN, WHITE, BLACK = 0, 1, 2

    def __init__(self, time_limit=5.0, debug=False, dfs_enabled=True):
        self.tlim = time_limit
        self.debug = debug
        self.dfs_enabled = dfs_enabled
        self.N = 0
        self.g = []       # grid
        self.fixed = []    # given cells
        self.nodes = 0
        self.t0 = 0
        self._stack = []     # assignment stack (r, c, v)
        self._trace = []   # solving trace for animation
        self._wc = self._bc = self._uc = 0
        self._timing = {}
        self._peri = ()
        self._visited = []
        self._visit_gen = 0

    def load(self, grid):
        self.N = len(grid)
        self.g = [row[:] for row in grid]
        self.fixed = [[False]*self.N for _ in range(self.N)]
        self._visited = [[0] * self.N for _ in range(self.N)]
        self._visit_gen = 0
        self._wc = self._bc = self._uc = 0
        self._timing.clear()
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
        self._peri = (
            [(0, c) for c in range(self.N)] +
            [(r, self.N - 1) for r in range(1, self.N)] +
            [(self.N - 1, c) for c in range(self.N - 2, -1, -1)] +
            [(r, 0) for r in range(self.N - 2, 0, -1)]
        )

    # ---- core assignment & propagation ----
    @_timeit('batch_set')
    def _batch_set(self, cells, v, *, rule_2x2=True, rule_corner3=True,
                   rule_surrounded=True, rule_bfs=True, rule_perimeter=True):
        """Set multiple cells to value v with a single propagation pass.
        Sets all cells first (grid + counters), then runs selected rules
        for each cell.  Keyword-only flags control which rules fire.
        _perimeter() is called only when rule_perimeter and at least one
        cell is on the grid boundary."""
        to_set = [(r, c) for r, c in cells if self.g[r][c] != v]
        if not to_set:
            return True
        for r, c in to_set:
            old = self.g[r][c]
            trace_step = len(self._trace)
            self._stack.append((trace_step, r, c, v))
            if old == 0: self._uc -= 1
            elif old == 1: self._wc -= 1
            else: self._bc -= 1
            if v == 0: self._uc += 1
            elif v == 1: self._wc += 1
            else: self._bc += 1
            self.g[r][c] = v
            self._trace.append((trace_step, r, c, v))
        opp_v = self.BLACK if v == self.WHITE else self.WHITE
        for r, c in to_set:
            if rule_2x2 and not self._rule_2x2_at(r, c):
                return False
            if rule_corner3 and not self._rule_corner3_at(r, c):
                return False
            if rule_surrounded and not self._rule_surrounded_at(r, c):
                return False
            if rule_bfs:
                if not self._bfs_comp(r, c):
                    return False
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.N and 0 <= nc < self.N and self.g[nr][nc] == opp_v:
                        if not self._bfs_comp(nr, nc):
                            return False
        if rule_perimeter and any(r == 0 or r == self.N - 1 or c == 0 or c == self.N - 1 for r, c in to_set):
            if self._perimeter() is None:
                return False
        return True

    def _set(self, r, c, v):
        """
        Set cell (r,c) to v and run all propagation rules.
        Delegates to _rule_2x2_at, _rule_corner3_at, _rule_surrounded_at,
        then checks bridge rule (BFS) and perimeter contiguity.
        Returns False on conflict, True otherwise.
        """
        old = self.g[r][c]
        if old == v:
            return True
        trace_step = len(self._trace)
        self._stack.append((trace_step, r, c, v))
        # update counts
        if old == 0: self._uc -= 1
        elif old == 1: self._wc -= 1
        else: self._bc -= 1
        if v == 0: self._uc += 1
        elif v == 1: self._wc += 1
        else: self._bc += 1
        self.g[r][c] = v
        self._trace.append((trace_step, r, c, v))

        if not self._rule_2x2_at(r, c):
            return False
        if not self._rule_corner3_at(r, c):
            return False

        if not self._rule_surrounded_at(r, c):
            return False

        # ---- bridge rule checks (component boundary) ----
        opp_v = self.BLACK if v == self.WHITE else self.WHITE
        if not self._bfs_comp(r, c):
            return False
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.N and 0 <= nc < self.N and self.g[nr][nc] == opp_v:
                if not self._bfs_comp(nr, nc):
                    return False

        # ---- perimeter check (only if cell is on boundary) ----
        if r == 0 or r == self.N - 1 or c == 0 or c == self.N - 1:
            p = self._perimeter()
            if p is None:
                return False

        return True

    # ---- extracted rule helpers (incremental, called from _set) ----
    @_timeit('2x2')
    def _rule_2x2_at(self, r, c):
        """Check 4 surrounding 2×2 blocks for Rules 1 & 2 after setting (r,c).
        Returns False on conflict, True otherwise."""
        N, g = self.N, self.g
        for dr in (-1, 0):
            for dc in (-1, 0):
                tr, tc = r + dr, c + dc
                if not (0 <= tr <= N - 2 and 0 <= tc <= N - 2):
                    continue
                cells = [(tr, tc), (tr, tc + 1), (tr + 1, tc), (tr + 1, tc + 1)]
                vv = [g[x][y] for x, y in cells]

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

                if uk is not None and (wc == 3 or bc == 3):
                    uv, ux, uy = (2, *cells[uk]) if wc == 3 else (1, *cells[uk])
                    if not self._set(ux, uy, uv):
                        return False
                    continue

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
        return True

    @_timeit('2x3_3x2')
    def _rule_corner3_at(self, r, c):
        """Check 2×3/3×2 corner Rule 5 after setting (r,c).
        Returns False on conflict, True otherwise."""
        N, g = self.N, self.g
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
        return True

    @_timeit('surrounded')
    def _rule_surrounded_at(self, r, c):
        """Check surrounded Rule 4 after setting (r,c).
        Case 1: UNKNOWN neighbor — all known neighbors same color.
        Case 2: (r,c) or colored neighbor has exactly 1 unknown, rest opposite.
        Returns False on conflict, True otherwise."""
        N, g = self.N, self.g
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

    def _snap(self):
        return len(self._stack)

    def _backtrack(self, snap_pos):
        while len(self._stack) > snap_pos:
            _, r, c, _ = self._stack.pop()
            cur = self.g[r][c]
            if cur == 0: self._uc -= 1
            elif cur == 1: self._wc -= 1
            else: self._bc -= 1
            self._uc += 1
            self.g[r][c] = 0
            trace_step = len(self._trace)
            self._trace.append((trace_step, r, c, 0))

    # ---- 2x2 full-grid preprocessing ----
    def _preprocess_2x2(self):
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
                    if not self._set(x, y, nv):
                        return None
                    changed = True
                    continue

                v0, v1, v2, v3 = vals
                if v0 != self.UNKNOWN and v0 == v3:
                    if v1 != self.UNKNOWN and v1 != v0 and v2 == self.UNKNOWN:
                        if not self._set(r + 1, c, v0):
                            return None
                        changed = True
                        continue
                    if v2 != self.UNKNOWN and v2 != v0 and v1 == self.UNKNOWN:
                        if not self._set(r, c + 1, v0):
                            return None
                        changed = True
                        continue
                if v1 != self.UNKNOWN and v1 == v2:
                    if v0 != self.UNKNOWN and v0 != v1 and v3 == self.UNKNOWN:
                        if not self._set(r + 1, c + 1, v1):
                            return None
                        changed = True
                        continue
                    if v3 != self.UNKNOWN and v3 != v1 and v0 == self.UNKNOWN:
                        if not self._set(r, c, v1):
                            return None
                        changed = True
                        continue
        return changed

    # ---- component analysis & bridge rule ----
    @_timeit('bfs')
    def _bfs_comp(self, r, c):
        """
        Bridge rule: BFS from colored cell (r,c) through same-color component.
        Cascades: forces unknowns one at a time and continues BFS to detect
        further forced cells, then batch-sets them with a single propagation pass.
        Returns False on conflict, True otherwise.
        """
        color = self.g[r][c]
        if color == self.UNKNOWN:
            return True
        total = self._wc if color == self.WHITE else self._bc

        self._visit_gen += 1
        gen = self._visit_gen
        visited = self._visited
        visited[r][c] = gen
        q = deque([(r, c)])
        found = 0  # actual same-color cells found
        unknown = None
        candidates = []

        while True:
            while q:
                cr, cc = q.popleft()
                if self.g[cr][cc] == color:
                    found += 1
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = cr + dr, cc + dc
                    if not (0 <= nr < self.N and 0 <= nc < self.N):
                        continue
                    nv = self.g[nr][nc]
                    if nv == color and visited[nr][nc] != gen:
                        visited[nr][nc] = gen
                        q.append((nr, nc))
                    elif nv == self.UNKNOWN and visited[nr][nc] != gen:
                        if unknown is None:
                            unknown = (nr, nc)
                        elif unknown != (nr, nc):
                            # 2+ boundaries → cascade what we have, don't force further
                            if candidates:
                                return self._batch_set(candidates, color, rule_bfs=False)
                            return True

            if found == total:
                if candidates:
                    return self._batch_set(candidates, color, rule_bfs=False)
                return True
            if unknown is None:
                return False

            # Cascade: this unknown is forced — add to candidates and expand
            candidates.append(unknown)
            visited[unknown[0]][unknown[1]] = gen
            q.append(unknown)
            unknown = None

    def _connectivity_expand(self):
        """
        Bridge rule via Union-Find with per-root unknown-neighbor sets.

        For each color with 2+ components, examine each component's unknown
        neighbor boundary count:
        - 0 unknown neighbors → conflict (component can never connect)
        - 1 unknown neighbor → force it to the component's color
        Returns True if any cell was changed, False if no changes.
        Returns None on conflict.
        """
        N = self.N
        g = self.g
        S = N * N
        parent = list(range(S))

        # adj_unknown[r] = set of unknown neighbor indices for root component r
        adj_unknown = [None] * S

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
            if adj_unknown[ry] is not None:
                if adj_unknown[rx] is None:
                    adj_unknown[rx] = adj_unknown[ry]
                else:
                    adj_unknown[rx] |= adj_unknown[ry]
                adj_unknown[ry] = None

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
                        ensure(adj_unknown, root).add(nidx)
                    elif not v and nv:
                        nroot = find(nidx)
                        ensure(adj_unknown, nroot).add(idx)
                    else:  # both unknown
                        ensure(adj_unknown, idx).add(nidx)
                        ensure(adj_unknown, nidx).add(idx)
                if r + 1 < N:
                    nv = g[r + 1][c]
                    nidx = (r + 1) * N + c
                    if v and nv:
                        if v == nv:
                            union(idx, nidx)
                    elif v and not nv:
                        root = find(idx)
                        ensure(adj_unknown, root).add(nidx)
                    elif not v and nv:
                        nroot = find(nidx)
                        ensure(adj_unknown, nroot).add(idx)
                    else:  # both unknown
                        ensure(adj_unknown, idx).add(nidx)
                        ensure(adj_unknown, nidx).add(idx)

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
                        if adj_unknown[nidx] is not None:
                            adj_unknown[nidx].discard(cell)
                    else:
                        nroot = find(nidx)
                        if adj_unknown[nroot] is not None:
                            adj_unknown[nroot].discard(cell)
            # Add new unknown neighbors from this cell
            my_root = find(cell)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < N and 0 <= nc < N):
                    continue
                if g[nr][nc] == 0:
                    ensure(adj_unknown, my_root).add(nr * N + nc)
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
                    b = len(adj_unknown[root]) if adj_unknown[root] else 0
                    if b == 0:
                        return None
                    if b == 1:
                        cell = next(iter(adj_unknown[root]))
                        ur, uc = divmod(cell, N)
                        if g[ur][uc] != color:
                            if not self._set(ur, uc, color):
                                return None
                            _absorb(cell, color, roots)
                            changed = True
                            if len(roots) < 2:
                                break

        return changed

    def _try_one_cell_both(self, r, c):
        """Try both colors on a single UNKNOWN cell (r,c).
        Returns:
          True  → cell was forced to a value (changed)
          False → conflict (unsolvable)
          None  → both colors viable, no change
        """
        sp = self._snap()
        ok_w = self._set(r, c, self.WHITE) and self._check_opposite_connectivity_at(r, c)
        self._backtrack(sp)

        if ok_w:
            sp = self._snap()
            ok_b = self._set(r, c, self.BLACK) and self._check_opposite_connectivity_at(r, c)
            self._backtrack(sp)
            if ok_b:
                return None
            # BLACK fails → force WHITE
            result = self._set(r, c, self.WHITE)
        else:
            # WHITE fails → force BLACK
            result = self._set(r, c, self.BLACK)

        if self.debug:
            if result:
                print(f"[try_both] 强制 ({r},{c}) = {'WHITE' if self.g[r][c] == self.WHITE else 'BLACK'}")
            else:
                print(f"[try_both] ({r},{c}) 冲突")
            self.pc()
        return result

    def _try_both(self):
        """
        For each unknown cell, try WHITE with full propagation.
        If WHITE fails → BLACK is forced (or unsolvable if BLACK also fails).
        If WHITE succeeds, try BLACK: if BLACK fails → WHITE is forced.
        If both OK → skip.
        Returns True if any cell was changed, False otherwise.
        """
        changed = False
        N = self.N
        g = self.g
        center = (N - 1) / 2
        cells = []
        for r in range(N):
            for c in range(N):
                if g[r][c] != self.UNKNOWN:
                    continue
                uk_cnt = 0
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < N and 0 <= nc < N and g[nr][nc] == self.UNKNOWN:
                        uk_cnt += 1
                dist = abs(r - center) + abs(c - center)
                cells.append((uk_cnt, dist, r, c))
        cells.sort()
        for _, _, r, c in cells:
            if self.g[r][c] != self.UNKNOWN:
                continue
            result = self._try_one_cell_both(r, c)
            if result is None:
                continue
            if not result:
                return False
            changed = True
        return changed

    def _propagate(self):
        """Apply perimeter until stable. Returns False on conflict."""
        while True:
            c1 = self._perimeter()
            if c1 is None:
                return False
            if not c1:
                break
        return True

    # ---- surrounded & single unknown neighbor (rule 4) ----
    def _surrounded(self):
        """
        Full-grid surrounded deduction (Rule 4).
        Case 1 — UNKNOWN cell: all known neighbors same color → set it.
        Case 2 — COLORED cell: exactly 1 unknown neighbor, rest opposite → set unknown.
        Returns True if any cell was changed, None on conflict.
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

    @_timeit('perimeter')
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

        peri = self._peri
        P = len(peri)
        # Keep only colored cells with their perimeter indices
        colored = [(i, self.g[r][c]) for i, (r, c) in enumerate(peri)
                   if self.g[r][c] != self.UNKNOWN]
        if not colored:
            return changed

        # Count transitions (color changes) and cells per color along perimeter
        transitions = 0
        wc = bc = 0
        for k in range(len(colored)):
            if colored[k][1] == self.WHITE: wc += 1
            else: bc += 1
            if colored[k][1] != colored[(k + 1) % len(colored)][1]:
                transitions += 1
        if transitions > 2:
            return None
        if transitions == 0:
            return changed  # only one color present, no arcs to constrain

        for color in (self.WHITE, self.BLACK):
            cnt = wc if color == self.WHITE else bc
            if cnt < 2:
                continue
            opp = self.BLACK if color == self.WHITE else self.WHITE
            idxs = [i for i, v in colored if v == color]

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
                # Fill unknowns on this arc in one batch
                arc_unknowns = [peri[a] for a in arc if self.g[peri[a][0]][peri[a][1]] == self.UNKNOWN]
                if arc_unknowns:
                    if not self._batch_set(arc_unknowns, color, rule_perimeter=False):
                        return None
                    changed = True

        return changed

    # ---- connectivity check (union-find) ----
    def _ok(self):
        """
        Final validation: connectivity via Union-Find.
        Each color must form at most 1 connected component.
        Also verifies no 2×2 block is all the same color.
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

    def _can_reach_all_same_color(self, color):
        """从 color 颜色的第一个 cell 出发 BFS，检查能否到达所有同色 cell。
        BFS 允许经过 UNKNOWN cell。找到所有目标后立即返回。"""
        N, g = self.N, self.g
        total = self._wc if color == self.WHITE else self._bc
        if total <= 1:
            return True

        first = None
        for r in range(N):
            for c in range(N):
                if g[r][c] == color:
                    first = (r, c)
                    break
            if first:
                break

        self._visit_gen += 1
        gen = self._visit_gen
        visited = self._visited
        q = deque([first])
        visited[first[0]][first[1]] = gen
        found = 1

        while q and found < total:
            cr, cc = q.popleft()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < N and 0 <= nc < N):
                    continue
                if visited[nr][nc] == gen:
                    continue
                nv = g[nr][nc]
                if nv == color or nv == self.UNKNOWN:
                    visited[nr][nc] = gen
                    q.append((nr, nc))
                    if nv == color:
                        found += 1
                        if found == total:
                            return True

        return found == total

    def _bfs_first_opp_from_unknown(self, sr, sc, opp):
        """从 UNKNOWN cell (sr,sc) 出发，仅在 UNKNOWN 中 BFS，
        返回遇到的第一个 O 色 cell，若无则返回 None。"""
        N, g = self.N, self.g
        self._visit_gen += 1
        gen = self._visit_gen
        visited = self._visited
        q = deque([(sr, sc)])
        visited[sr][sc] = gen
        while q:
            cr, cc = q.popleft()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < N and 0 <= nc < N):
                    continue
                if visited[nr][nc] == gen:
                    continue
                nv = g[nr][nc]
                if nv == opp:
                    return (nr, nc)
                if nv == self.UNKNOWN:
                    visited[nr][nc] = gen
                    q.append((nr, nc))
        return None

    def _check_opposite_connectivity_at(self, r, c):
        """给定已染色 cell (r,c)，检查其对立色 O 在 (r,c) 周边
        是否仍能通过 UNKNOWN 保持连通。
        若 (r,c) 为 UNKNOWN 或记录到的 O cell ≤1 个 → True。
        记录规则：若邻居为 O 直接记录；若邻居为 UNKNOWN 则 BFS 经 UNKNOWN
        找到第一个 O 并记录。若 2+ 个 O cell 不能相互到达 → False。"""
        g = self.g
        if g[r][c] == self.UNKNOWN:
            return True
        color = g[r][c]
        opp = self.BLACK if color == self.WHITE else self.WHITE
        N = self.N

        recorded = set()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < N and 0 <= nc < N):
                continue
            nv = g[nr][nc]
            if nv == opp:
                recorded.add((nr, nc))
            elif nv == self.UNKNOWN:
                found = self._bfs_first_opp_from_unknown(nr, nc, opp)
                if found is not None:
                    recorded.add(found)

        if len(recorded) <= 1:
            return True

        # BFS from first recorded through O+UNKNOWN to reach all recorded
        self._visit_gen += 1
        gen = self._visit_gen
        visited = self._visited
        first = next(iter(recorded))
        q = deque([first])
        visited[first[0]][first[1]] = gen
        reachable = {first}

        while q and len(reachable) < len(recorded):
            cr, cc = q.popleft()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < N and 0 <= nc < N):
                    continue
                if visited[nr][nc] == gen:
                    continue
                nv = g[nr][nc]
                if nv == opp or nv == self.UNKNOWN:
                    visited[nr][nc] = gen
                    q.append((nr, nc))
                    if nv == opp and (nr, nc) in recorded:
                        reachable.add((nr, nc))

        return len(reachable) == len(recorded)

    # ---- cell selection ----
    def _pick(self):
        """Pick unknown cell closest to the last assigned cell (Manhattan distance).
        Falls back to row-major first unknown when _stack is empty."""
        N, g = self.N, self.g
        if self._stack:
            _, pr, pc, _ = self._stack[-1]
            best, best_dist = None, N * N
            for r in range(N):
                for c in range(N):
                    if g[r][c] == self.UNKNOWN:
                        d = abs(r - pr) + abs(c - pc)
                        if d < best_dist:
                            best_dist = d
                            best = (r, c)
            return best
        # First call — row-major first unknown
        for r in range(N):
            for c in range(N):
                if g[r][c] == self.UNKNOWN:
                    return (r, c)
        return None

    # ---- DFS ----
    def solve(self):
        self.t0 = time.time()
        self.nodes = 0
        self._stack = []
        self._trace = []
        self._initial_grid = [row[:] for row in self.g]
        # Preprocessing: perimeter → 2×2 → corner3 → surrounded → connectivity_expand
        # Then try_both forced-cell loop, then DFS if still unsolved.
        if self._perimeter() is None:
            return False
        if self._preprocess_2x2() is None:
            return False
        if self._corner3() is None:
            return False
        if self._surrounded() is None:
            return False
        if self._connectivity_expand() is None:
            return False
        if self._done():
            return True
        # Try-both: before DFS, try each unknown with both colors.
        # If one color causes conflict, the other is forced.
        if self.debug:
            print(f"\n── Try-Both Round 0 ──")
            self.pc()
        _try_round = 0
        while True:
            _try_round += 1
            tb = self._try_both()
            if not tb:
                break
            if self.debug:
                print(f"\n── Try-Both Round {_try_round} ──")
                self.pc()
            if self._done():
                return True
        if self.dfs_enabled:
            return self._dfs()
        return False

    def _dfs(self):
        if time.time() - self.t0 > self.tlim:
            return False
        self.nodes += 1
        cell = self._pick()
        if cell is None:
            return self._ok()
        r, c = cell
        wc = bc = 0
        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
            nr, nc = r+dr, c+dc
            if 0 <= nr < self.N and 0 <= nc < self.N:
                if self.g[nr][nc] == self.WHITE: wc += 1
                elif self.g[nr][nc] == self.BLACK: bc += 1
        order = [self.WHITE, self.BLACK] if wc >= bc else [self.BLACK, self.WHITE]
        for co in order:
            sp = self._snap()
            if self._set(r, c, co):
                # Try both on UNKNOWN cells in 5×5 neighborhood
                ok = True
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.N and 0 <= nc < self.N and self.g[nr][nc] == self.UNKNOWN:
                            if self._try_one_cell_both(nr, nc) is False:
                                ok = False
                                break
                    if not ok:
                        break
                if ok and self._dfs():
                    return True
            self._backtrack(sp)
        return False

    # ---- animation ----
    def animate(self, delay=None, full_trace=False):
        """Animate solving process.
        full_trace=True: replay self._trace (all steps including backtracking).
        full_trace=False: replay self._stack (final assignments only, clean)."""
        import time as _time
        import os as _os
        import sys as _sys
        if delay is None:
            delay = 0.02
        self.g = [row[:] for row in self._initial_grid]
        steps = self._trace if full_trace else self._stack
        total = len(self._trace)
        # Initialize live counters from initial grid
        wc = sum(row.count(self.WHITE) for row in self.g)
        bc = sum(row.count(self.BLACK) for row in self.g)
        uc = sum(row.count(self.UNKNOWN) for row in self.g)
        _os.system('clear')
        print(f"初始谜题 ({total} 步待求解)")
        self.pc()
        _time.sleep(2)
        WB = "\033[47m\033[30m"; BB = "\033[40m\033[97m"; GB = "\033[100m\033[97m"; RE = "\033[0m"
        _pw = len(str(total))
        _fw = len(str(self.N * self.N))
        for step, r, c, v in steps:
            old = self.g[r][c]
            if old == 0: uc -= 1
            elif old == 1: wc -= 1
            else: bc -= 1
            if v == 0: uc += 1
            elif v == 1: wc += 1
            else: bc += 1
            self.g[r][c] = v
            remaining = total - step - 1
            # Update progress title (row 1)
            _sys.stdout.write(f"\033[1;1H求解进度: {remaining:>{_pw}}/{total} 步待执行" + " " * 20)
            # Update cell
            _sys.stdout.write(f"\033[{r + 4};{4 + c * 3}H")
            if v == self.WHITE:
                _sys.stdout.write(f"{WB} ○ {RE}")
            elif v == self.BLACK:
                _sys.stdout.write(f"{BB} ● {RE}")
            else:
                _sys.stdout.write(f"{GB} · {RE}")
            # Update live counters below grid
            _sys.stdout.write(f"\033[{self.N + 6};1H{WB} ○ {wc:>{_fw}} {RE}{BB} ● {bc:>{_fw}} {RE}{GB} · {uc:>{_fw}} {RE}   ")
            _sys.stdout.write(f"\033[{self.N + 7};1H")
            _sys.stdout.flush()
            _time.sleep(delay)
        _time.sleep(2)

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
        print(f"       trace={len(self._trace)}  stack={len(self._stack)}  uc={self._uc}")

    def ps(self, elapsed=None, show_grid=True):
        RE = "\033[0m"; BO = "\033[1m"
        print(f"\n{BO}结果{RE}")
        print("=" * 50)
        if show_grid:
            self.pc()
        wc = sum(1 for r in range(self.N) for c in range(self.N) if self.g[r][c]==self.WHITE)
        bc = sum(1 for r in range(self.N) for c in range(self.N) if self.g[r][c]==self.BLACK)
        print(f"○白={wc} ●黑={bc} 总={self.N*self.N}")
        ok = self._ok()
        print(f"验证: {'✓' if ok else '✗'}")
        t = elapsed if elapsed is not None else time.time() - self.t0
        print(f"时间={t:.3f}s 节点={self.nodes} trace={len(self._trace)}")
        if self._timing:
            parts = [f"2×2={self._timing.get('2x2',0)*1000:.1f}ms",
                     f"2×3/3×2={self._timing.get('2x3_3x2',0)*1000:.1f}ms",
                     f"surrounded={self._timing.get('surrounded',0)*1000:.1f}ms",
                     f"bfs={self._timing.get('bfs',0)*1000:.1f}ms",
                     f"batch={self._timing.get('batch_set',0)*1000:.1f}ms",
                     f"perimeter={self._timing.get('perimeter',0)*1000:.1f}ms"]
            print("  " + " | ".join(p for p in parts if not p.startswith("0.")))
        print("=" * 50)

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


def solve(grid, tl=5.0, debug=True):
    s = Solver(time_limit=tl, debug=debug)
    s.load(grid)
    if debug:
        print(f"\n{s.N}x{s.N}")
        s.pc()
    ok = s.solve()
    if ok and debug: s.ps()
    elif not ok and debug: print(f"\n❌ ({s.nodes} nodes)")
    return ok, s
