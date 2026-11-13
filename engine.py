"""Rolling Kendall tau-b engine with incremental window state.

State maintenance summary
-------------------------
For the current window, only valid points (both coordinates non-null) take
part in the statistics.  We keep, with size bounded by the window width W:

* ``_rows``: deque of the last W validated rows (missing rows included, as
  placeholders that never enter the index).
* ``_blocks``: sqrt-decomposed sorted multiset of the valid points.  Each block
  holds parallel ``xs``/``ys`` lists kept sorted by x and a sorted copy ``sy``
  of the y values.  Blocks stay between ``B//2`` and ``2B`` points via
  split/merge, so block count and block size are both O(sqrt(n)).  This gives
  O(sqrt(n)) 2-D quadrant counts, inserts and deletes without any per-window
  sort or full scan of the valid points.
* ``_cx``/``_cy``/``_cxy``: multiplicity dicts underlying tx, ty, txy
  (sums of C2(group size)); updated by one hash lookup per push.
* ``_inv``: number of unordered pairs with different x and different y whose
  y order disagrees with their x order (the same strict-inversion count the
  reference obtains by sorting by (x, y) and counting y inversions).  When a
  point p joins or leaves, one block walk returns its four quadrant counts;
  its inversion contribution is left/above (x'<x, y'>y) plus right/below
  (x'>x, y'<y), applied with + on insert and - on delete.

Then per window, with ``pairs = C2(n)``::

    S   = pairs - tx - ty + txy - 2*inv
    Dx  = pairs - tx
    Dy  = pairs - ty
    tau = S / sqrt(Dx*Dy)   (or None when either denominator factor is zero)

All of n, S, Dx, Dy stay exact Python ints.  The first full window builds the
index once in bulk (including a Fenwick-tree pass for the initial inversion
count); later pushes only touch O(sqrt(W)) state.  Input is consumed one row
at a time, no future rows are read and no whole-stream coordinate dictionary
is retained.
"""
from bisect import bisect_left, bisect_right, insort_left
from collections import deque

from reference import validate_row, validate_width

# Target block size.  Chosen so block count (~n/B) and per-block scans (at
# most two straddling blocks) stay small; split at 2B, merge below B//2.
_BLOCK = 192


class _Block:
    __slots__ = ("xs", "ys", "sy", "xmax")

    def __init__(self, xs, ys, sy):
        self.xs = xs          # sorted by x (parallel to ys)
        self.ys = ys
        self.sy = sy          # sorted copy of ys
        self.xmax = xs[-1]


class Engine:
    def __init__(self, W):
        self.W = validate_width(W)
        self._rows = deque()
        self._blocks = []
        self._cx = {}
        self._cy = {}
        self._cxy = {}
        self._n = 0
        self._tx = 0
        self._ty = 0
        self._txy = 0
        self._inv = 0
        self._built = False

    # ------------------------------------------------------------------
    # Multiplicity bookkeeping.  Adding the k-th copy raises C2 by k-1;
    # removing a copy lowers C2 by the remaining copy count.
    @staticmethod
    def _bump(counter, key):
        k = counter.get(key, 0) + 1
        counter[key] = k
        return k - 1

    @staticmethod
    def _drop(counter, key):
        k = counter[key] - 1
        if k:
            counter[key] = k
        else:
            del counter[key]
        return k

    # ------------------------------------------------------------------
    def _build_index(self):
        """Bulk construction for the first full window (one-off O(W log W))."""
        pts = sorted((x, y) for x, y in self._rows
                     if x is not None and y is not None)
        n = len(pts)

        cx, cy, cxy = {}, {}, {}
        tx = ty = txy = 0
        for x, y in pts:
            k = cx.get(x, 0) + 1
            cx[x] = k
            tx += k - 1
            k = cy.get(y, 0) + 1
            cy[y] = k
            ty += k - 1
            key = (x, y)
            k = cxy.get(key, 0) + 1
            cxy[key] = k
            txy += k - 1

        # Sorted blocks.
        blocks = []
        B = _BLOCK
        for lo in range(0, n, B):
            chunk = pts[lo:lo + B]
            xs = [p[0] for p in chunk]
            ys = [p[1] for p in chunk]
            blocks.append(_Block(xs, ys, sorted(ys)))

        # Initial inversion count via a Fenwick tree over compressed y ranks.
        # Points are already sorted by (x, y): equal-x groups are contiguous
        # and internally y-ascending, so they never contribute strict
        # inversions; only pairs with x'<x and y'>y are counted.
        inv = 0
        if n:
            ys_all = [p[1] for p in pts]
            order = sorted(range(n), key=ys_all.__getitem__)
            ranks = [0] * n
            prev = None
            cur_rank = 0
            for pos, idx in enumerate(order):
                val = ys_all[idx]
                if val != prev:
                    cur_rank = pos + 1
                    prev = val
                ranks[idx] = cur_rank
            bit = [0] * (n + 1)
            seen = 0
            for i in range(n):
                r = ranks[i]
                s = 0
                j = r
                while j:
                    s += bit[j]
                    j -= j & -j
                inv += seen - s
                j = r
                while j <= n:
                    bit[j] += 1
                    j += j & -j
                seen += 1

        self._blocks = blocks
        self._cx = cx
        self._cy = cy
        self._cxy = cxy
        self._n = n
        self._tx = tx
        self._ty = ty
        self._txy = txy
        self._inv = inv
        self._built = True

    # ------------------------------------------------------------------
    def _locate_block(self, x):
        blocks = self._blocks
        lo, hi = 0, len(blocks)
        while lo < hi:
            mid = (lo + hi) >> 1
            if blocks[mid].xmax < x:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _insert_point(self, x, y):
        blocks = self._blocks
        if not blocks:
            blocks.append(_Block([x], [y], [y]))
            return
        bi = self._locate_block(x)
        if bi == len(blocks):
            bi -= 1
        b = blocks[bi]
        i = bisect_left(b.xs, x)
        b.xs.insert(i, x)
        b.ys.insert(i, y)
        insort_left(b.sy, y)
        b.xmax = b.xs[-1]
        if len(b.xs) > 2 * _BLOCK:
            mid = len(b.xs) // 2
            left = _Block(b.xs[:mid], b.ys[:mid], sorted(b.ys[:mid]))
            right = _Block(b.xs[mid:], b.ys[mid:], sorted(b.ys[mid:]))
            blocks[bi:bi + 1] = [left, right]

    def _delete_point(self, x, y):
        blocks = self._blocks
        bi = self._locate_block(x)
        # Locate the exact (x, y) copy inside the contiguous equal-x run.
        # The run starts in this block and may continue into the next one;
        # same-x copies with other y values must not be mistaken for it.
        while True:
            b = blocks[bi]
            i = bisect_left(b.xs, x)
            end = bisect_right(b.xs, x)
            for k in range(i, end):
                if b.ys[k] == y:
                    i = k
                    break
            else:
                bi += 1  # run continues in the next block
                continue
            break
        del b.xs[i]
        del b.ys[i]
        b.sy.pop(bisect_left(b.sy, y))
        if not b.xs:
            del blocks[bi]
            return
        b.xmax = b.xs[-1]
        if len(b.xs) < _BLOCK // 2 and len(blocks) > 1:
            if bi > 0:
                nb = blocks[bi - 1]
                if len(nb.xs) + len(b.xs) <= 2 * _BLOCK:
                    pairs = sorted(zip(nb.xs + b.xs, nb.ys + b.ys))
                    xs = [p[0] for p in pairs]
                    ys = [p[1] for p in pairs]
                    blocks[bi - 1:bi + 1] = [_Block(xs, ys, sorted(ys))]
                    return
            nb = blocks[bi + 1] if bi + 1 < len(blocks) else None
            if nb is not None and len(nb.xs) + len(b.xs) <= 2 * _BLOCK:
                pairs = sorted(zip(b.xs + nb.xs, b.ys + nb.ys))
                xs = [p[0] for p in pairs]
                ys = [p[1] for p in pairs]
                blocks[bi:bi + 2] = [_Block(xs, ys, sorted(ys))]

    def _quadrants(self, x, y):
        """Return (ll, lg, rl, rg): counts of points with
        x'<x,y'<y / x'<x,y'>y / x'>x,y'<y / x'>x,y'>y.
        Equal-x or equal-y points are excluded on that axis.

        Blocks are ordered by x.  Those wholly below x answer from their
        sorted y copy via bisect; the (at most two) blocks containing the
        equal-x run are scanned point by point; remaining blocks are wholly
        above x and again answer via bisect."""
        ll = lg = rl = rg = 0
        blocks = self._blocks
        first = self._locate_block(x)  # first block with xmax >= x
        # Fully-left blocks: every point has x' < x.
        for b in blocks[:first]:
            sy = b.sy
            ll += bisect_left(sy, y)
            lg += len(sy) - bisect_right(sy, y)
        # Straddling block(s): blocks first..last-1 each contain some point
        # with x' <= x; only they can hold x'<x points or the equal-x run.
        # At most two such blocks need a point-by-point scan.
        bi = first
        while bi < len(blocks) and blocks[bi].xmax <= x:
            b = blocks[bi]
            for xx, yy in zip(b.xs, b.ys):
                if xx < x:
                    if yy < y:
                        ll += 1
                    elif yy > y:
                        lg += 1
                # xx == x contributes nothing (x-axis tie).
            bi += 1
        # bi now points at the first block whose xmax > x; that block still
        # needs scanning for its x'<x and x'>x portions (its equal-x tail,
        # if any, contributes nothing).
        if bi < len(blocks):
            b = blocks[bi]
            for xx, yy in zip(b.xs, b.ys):
                if xx < x:
                    if yy < y:
                        ll += 1
                    elif yy > y:
                        lg += 1
                elif xx > x:
                    if yy < y:
                        rl += 1
                    elif yy > y:
                        rg += 1
            bi += 1
        # Fully-right blocks: every point has x' > x.
        for b in blocks[bi:]:
            sy = b.sy
            rl += bisect_left(sy, y)
            rg += len(sy) - bisect_right(sy, y)
        return ll, lg, rl, rg

    # ------------------------------------------------------------------
    def push(self, row):
        point = validate_row(row)
        rows = self._rows
        full = len(rows) == self.W
        old = rows.popleft() if full else None
        rows.append(point)

        if not self._built:
            if len(rows) < self.W:
                return None
            self._build_index()
            return self._summary()

        # Remove the evicted point's contributions before inserting the new
        # one, so quadrant counts never include the point being updated.
        if old is not None:
            ox, oy = old
            if ox is not None and oy is not None:
                _, lg, rl, _ = self._quadrants(ox, oy)
                # Inversions involving the leaving point: left/above plus
                # right/below (the two opposite-order pair orientations).
                self._inv -= lg + rl
                self._delete_point(ox, oy)
                self._n -= 1
                self._tx -= self._drop(self._cx, ox)
                self._ty -= self._drop(self._cy, oy)
                self._txy -= self._drop(self._cxy, (ox, oy))

        x, y = point
        if x is not None and y is not None:
            _, lg, rl, _ = self._quadrants(x, y)
            # Inversions created with existing points: left/above plus
            # right/below (both are opposite-order pairs with this point).
            self._inv += lg + rl
            self._insert_point(x, y)
            self._n += 1
            self._tx += self._bump(self._cx, x)
            self._ty += self._bump(self._cy, y)
            self._txy += self._bump(self._cxy, (x, y))

        return self._summary()

    def _summary(self):
        n = self._n
        pairs = n * (n - 1) // 2
        dx = pairs - self._tx
        dy = pairs - self._ty
        s = pairs - self._tx - self._ty + self._txy - 2 * self._inv
        tau = s / (dx * dy) ** 0.5 if dx and dy else None
        return {"n": n, "S": s, "Dx": dx, "Dy": dy, "tau": tau}
