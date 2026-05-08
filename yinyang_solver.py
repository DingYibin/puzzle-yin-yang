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
        Returns True if any cell was changed, False otherwise.
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
                        # v1 opposite known, v2 unknown → v2 = v0
                        if v1 != self.UNKNOWN and v1 != v0 and v2 == self.UNKNOWN:
                            changed = True
                            self._set(r+1, c, v0)
                            hit = True
                            continue
                        # v2 opposite known, v1 unknown → v1 = v0
                        if v2 != self.UNKNOWN and v2 != v0 and v1 == self.UNKNOWN:
                            changed = True
                            self._set(r, c+1, v0)
                            hit = True
                            continue
                    # Case 2: diagonal / (v1==v2)
                    if v1 != self.UNKNOWN and v1 == v2:
                        # v0 opposite known, v3 unknown → v3 = v1
                        if v0 != self.UNKNOWN and v0 != v1 and v3 == self.UNKNOWN:
                            changed = True
                            self._set(r+1, c+1, v1)
                            hit = True
                            continue
                        # v3 opposite known, v0 unknown → v0 = v1
                        if v3 != self.UNKNOWN and v3 != v1 and v0 == self.UNKNOWN:
                            changed = True
                            self._set(r, c, v1)
                            hit = True
                            continue

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

    def _propagate(self):
        """Apply deduction rules until stable (p2 + bridge + perimeter)."""
        while True:
            c1 = self._p2()
            s2 = self._sn()
            if not self._bridge():
                return False
            c2 = (self._sn() != s2)
            s3 = self._sn()
            if not self._perimeter():
                return False
            c3 = (self._sn() != s3)
            if not c1 and not c2 and not c3:
                break
        return True

    # ---- surrounded rule (rule 4) ----
    def _surrounded(self):
        """
        Rule 4: if all EXISTING orthogonal neighbors of an unknown cell
        are known and the same color, that cell must also be that color.
        (For interior cells this means all 4 neighbors; for edges, 2-3.)
        """
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] != self.UNKNOWN:
                    continue
                color = None
                all_known = True
                for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < self.N and 0 <= nc < self.N:
                        v = self.g[nr][nc]
                        if v == self.UNKNOWN:
                            all_known = False
                            break
                        if color is None:
                            color = v
                        elif v != color:
                            all_known = False
                            break
                if all_known and color is not None:
                    if self.fixed[r][c] and self.g[r][c] != color:
                        return False
                    if self.g[r][c] != color:
                        self._set(r, c, color)
        return True
    def _perimeter(self):
        """
        Rule 3: perimeter cells of same color form contiguous arcs.
        If two cells of color C are on the perimeter with only unknowns
        between them (no opposite color), those unknowns must be C,
        UNLESS forcing them would create an immediate 2×2 violation.
        """
        N = self.N
        if N <= 2:
            return True

        # Extract perimeter in clockwise order
        peri = []
        for c in range(N):
            peri.append((0, c))
        for r in range(1, N):
            peri.append((r, N-1))
        for c in range(N-2, -1, -1):
            peri.append((N-1, c))
        for r in range(N-2, 0, -1):
            peri.append((r, 0))

        P = len(peri)

        for color in (self.WHITE, self.BLACK):
            opp = self.BLACK if color == self.WHITE else self.WHITE

            color_idx = [i for i in range(P) if self.g[peri[i][0]][peri[i][1]] == color]

            if len(color_idx) < 2:
                continue

            for idx in range(len(color_idx)):
                i = color_idx[idx]
                j = color_idx[(idx + 1) % len(color_idx)]

                if i < j:
                    arc_indices = list(range(i + 1, j))
                else:
                    arc_indices = list(range(i + 1, P)) + list(range(0, j))

                if not arc_indices:
                    continue

                has_opp = False
                for a in arc_indices:
                    ar, ac = peri[a]
                    if self.g[ar][ac] == opp:
                        has_opp = True
                        break

                if has_opp:
                    continue

                # Force unknowns on this arc, but check 2×2 safety
                for a in arc_indices:
                    ar, ac = peri[a]
                    if self.g[ar][ac] == self.UNKNOWN:
                        if self.fixed[ar][ac]:
                            return False
                        # Check: would setting (ar, ac) to 'color' create a 2×2 all-same?
                        safe = True
                        for dr in (-1, 0):
                            for dc in (-1, 0):
                                cr, cc = ar + dr, ac + dc
                                if 0 <= cr < N-1 and 0 <= cc < N-1:
                                    others = [(x,y) for x,y in
                                              [(cr,cc),(cr,cc+1),(cr+1,cc),(cr+1,cc+1)]
                                              if (x,y) != (ar,ac)]
                                    if all(self.g[x][y] == color for x,y in others):
                                        safe = False
                                        break
                            if not safe:
                                break
                        if safe:
                            self._set(ar, ac, color)

        return True

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

        return len(white_roots) <= 1 and len(black_roots) <= 1

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
        if not self._propagate():
            return False
        if not self._surrounded():
            return False
        if self.verbose:
            self.pc()
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
            if self._propagate():
                self._surrounded()
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
