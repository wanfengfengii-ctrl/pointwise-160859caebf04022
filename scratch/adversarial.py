"""Adversarial differential + state-bound tests beyond the main diff suite."""
import math
import random
import sys

sys.path.insert(0, "/workspace")

from engine import Engine
from reference import summarize, _choose2


def same(got, want):
    assert (got is None) == (want is None)
    if want is None:
        return
    for k in ("n", "S", "Dx", "Dy"):
        assert type(got[k]) is int and got[k] == want[k], (k, got, want)
    if want["tau"] is None:
        assert got["tau"] is None
    else:
        assert math.isclose(got["tau"], want["tau"], rel_tol=1e-12, abs_tol=1e-12)


def block_invariants(e):
    B = 192
    blocks = e._blocks
    if not e._n:
        assert blocks == []
        return
    total = 0
    prev_max = None
    for bi, b in enumerate(blocks):
        assert b.xs == sorted(b.xs)
        assert b.sy == sorted(b.ys)
        assert len(b.xs) == len(b.ys) == len(b.sy)
        assert b.xmax == b.xs[-1]
        assert len(b.xs) <= 2 * B
        # A block can stay small only when neither neighbor fits within 2B;
        # block count stays O(n/B), so assert the global bound instead of a
        # per-block floor the merge policy does not guarantee.
        if prev_max is not None:
            assert prev_max <= b.xs[0]
        prev_max = b.xmax
        total += len(b.xs)
    assert total == e._n
    # Number of blocks bounded by the split policy: at most n/(B//2) + 1.
    assert len(blocks) <= max(1, 2 * total // B) + 1


def run(W, rows):
    e = Engine(W)
    hist = []
    for row in rows:
        hist.append(tuple(row))
        got = e.push(row)
        if len(hist) >= W:
            same(got, summarize(hist[-W:]))
        if e._built:
            block_invariants(e)
            # Counter consistency.
            assert sum(e._cx.values()) == e._n
            assert sum(e._cy.values()) == e._n
            assert sum(e._cxy.values()) == e._n
    return e


def main():
    rng = random.Random(424242)

    # A. Long heavy-ties stream across many block splits AND merges.
    e = run(777, [[rng.randrange(5), rng.randrange(5)] for _ in range(6000)])
    # State must not grow with total input: bounded by window, not stream.
    assert len(e._rows) == 777
    assert sum(len(b.xs) for b in e._blocks) <= 777

    # B. All-missing windows then recovery (index empties out and regrows).
    rows = [[None, None]] * 800 + [[rng.randrange(10), rng.randrange(10)]
                                   for _ in range(800)] + [[None, 3], [3, None]] * 300
    run(200, rows)

    # C. Alternating valid / missing so index repeatedly shrinks to tiny.
    rows = []
    for i in range(3000):
        if i % 3 == 0:
            rows.append([None, rng.randrange(100)])
        elif i % 3 == 1:
            rows.append([rng.randrange(100), None])
        else:
            rows.append([rng.randrange(100), rng.randrange(100)])
    run(333, rows)

    # D. Every point identical for a long run, then distinct, then identical.
    rows = [[4, 4]] * 1500 + [[i, i] for i in range(1500)] + [[4, 4]] * 1500
    run(500, rows)

    # E. Extreme big integers and sign extremes (exact arithmetic).
    big = 10 ** 200
    rows = [[rng.choice([big, -big, 0, big - 1, -big + 1]),
             rng.choice([big, -big, 0, big - 1, -big + 1])] for _ in range(2000)]
    run(401, rows)

    # F. Width 1: every window has at most one point, all denominators zero.
    e = run(1, [[i, i] for i in range(500)] + [[None, 1]] * 50)
    assert e._summary()["tau"] is None

    # G. Width larger than total input: never builds, always None.
    e = Engine(10_000)
    for i in range(100):
        assert e.push([i, -i]) is None
    assert e._built is False and e._blocks == []

    # H. Huge width value is accepted (arbitrary precision int), push once.
    assert Engine(10 ** 40).push([1, 2]) is None

    # I. Invalid row does not consume a slot and leaves state untouched.
    e = Engine(4)
    e.push([1, 1]); e.push([2, 2])
    snapshot = (list(e._rows), e._n, e._inv, e._tx, e._ty, e._txy)
    for bad in ([True, 1], [1, 2, 3], [1.0, 2], ["x", 2], [None, bool]):
        try:
            e.push(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(bad)
    assert (list(e._rows), e._n, e._inv, e._tx, e._ty, e._txy) == snapshot
    # tuple input works and caller tuple is not retained mutably (it's copied).
    t = (9, 9)
    e.push(t)
    assert len(e._rows) == 3

    # J. Returned dicts are independent and hold exact int types.
    e = Engine(2)
    e.push([1, 3]); o1 = e.push([2, 4])
    o2 = e.push([3, 5])
    assert o1 is not o2
    for k in ("n", "S", "Dx", "Dy"):
        assert isinstance(o2[k], int) and type(o2[k]) is int

    # K. Choose2 bookkeeping matches Counter-derived tx/ty/txy at random times.
    from collections import Counter
    rng = random.Random(7)
    W = 250
    e = Engine(W)
    hist = []
    for i in range(1200):
        row = [rng.randrange(6), rng.randrange(6)]
        hist.append(tuple(row))
        e.push(row)
        if i >= W and i % 97 == 0:
            pts = [p for p in hist[-W:] if None not in p]
            tx = sum(_choose2(k) for k in Counter(x for x, y in pts).values())
            ty = sum(_choose2(k) for k in Counter(y for x, y in pts).values())
            txy = sum(_choose2(k) for k in Counter(pts).values())
            assert (e._tx, e._ty, e._txy) == (tx, ty, txy)

    print("ADVERSARIAL_OK")


if __name__ == "__main__":
    main()
