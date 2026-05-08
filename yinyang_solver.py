"""
Yin-Yang Puzzle Solver
状态: 0=未知, 1=白色, 2=黑色
策略: DFS + 2×2 传播 + 桥规则 (连通分量边界检查)
"""
import time
from collections import deque


class Solver:
    UNKNOWN, WHITE, BLACK = 0, 1, 2

    def __init__(self, time_limit=5.0):
        self.tlim = time_limit
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

    # ---- 2x2 propagation ----
    def _p2(self):
        while True:
            hit = False
            for r in range(self.N-1):
                for c in range(self.N-1):
                    uk = None
                    wc = bc = 0
                    for rr, cc in ((r,c),(r,c+1),(r+1,c),(r+1,c+1)):
                        v = self.g[rr][cc]
                        if v == self.UNKNOWN: uk = (rr, cc)
                        elif v == self.WHITE: wc += 1
                        else: bc += 1
                    if uk and (wc == 3 or bc == 3):
                        rr, cc = uk
                        nv = self.BLACK if wc == 3 else self.WHITE
                        if self.fixed[rr][cc] and self.g[rr][cc] != nv:
                            return False
                        if self.g[rr][cc] != nv:
                            self._set(rr, cc, nv)
                            hit = True
            if not hit:
                break
        return True

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
        """Bridge rule: component with 1 boundary → forced. Also check 0 boundary → conflict."""
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
        """Apply all propagation until stable"""
        while True:
            s1 = self._sn()
            if not self._p2():
                return False
            c1 = (self._sn() != s1)
            s2 = self._sn()
            if not self._bridge():
                return False
            c2 = (self._sn() != s2)
            if not c1 and not c2:
                break
        return True

    # ---- connectivity check (full grid) ----
    def _conn(self, color):
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] == color:
                    seen = [[False]*self.N for _ in range(self.N)]
                    q = deque([(r,c)])
                    seen[r][c] = True
                    cnt = 0
                    while q:
                        cr, cc = q.popleft()
                        cnt += 1
                        for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                            nr, nc = cr+dr, cc+dc
                            if 0 <= nr < self.N and 0 <= nc < self.N and not seen[nr][nc] and self.g[nr][nc] == color:
                                seen[nr][nc] = True
                                q.append((nr, nc))
                    return cnt == sum(1 for r2 in range(self.N) for c2 in range(self.N) if self.g[r2][c2] == color)
        return True

    def _ok(self):
        return self._conn(self.WHITE) and self._conn(self.BLACK)

    def _done(self):
        for r in range(self.N):
            for c in range(self.N):
                if self.g[r][c] == self.UNKNOWN:
                    return False
        return True

    # ---- cell selection ----
    def _pick(self):
        """Pick from smallest multi-component boundary; else most constrained."""
        best, best_sc = None, -1
        for color in (self.WHITE, self.BLACK):
            comps = self._find_comps(color)
            if len(comps) >= 2:
                smallest = min(comps, key=lambda c: c[0])
                for br, bc in smallest[1]:
                    sc = sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                            if 0 <= br+dr < self.N and 0 <= bc+dc < self.N and self.g[br+dr][bc+dc])
                    sc = sc * 1000
                    if sc > best_sc:
                        best_sc = sc
                        best = (br, bc)
        if best:
            return best
        for color in (self.WHITE, self.BLACK):
            for _, boundary in self._find_comps(color):
                for br, bc in boundary:
                    sc = sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                            if 0 <= br+dr < self.N and 0 <= bc+dc < self.N and self.g[br+dr][bc+dc])
                    sc = sc * 100
                    if sc > best_sc:
                        best_sc = sc
                        best = (br, bc)
        if best:
            return best
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
    s = Solver(time_limit=tl)
    s.load(grid)
    if vb:
        print(f"\n{s.N}x{s.N}")
        s.pc()
    ok = s.solve()
    if ok and vb: s.ps()
    elif not ok and vb: print(f"\n❌ ({s.nodes} nodes)")
    return ok, s
