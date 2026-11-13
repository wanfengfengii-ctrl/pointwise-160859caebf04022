"""Exhaustive per-window differential test: engine vs reference.summarize.

Runs many random and adversarial streams across many widths, comparing every
single window dict (exact ints n/S/Dx/Dy, tau within tolerance), plus
invalid-input non-consumption and caller-row immutability.  Pure stdlib.
"""
import math
import random
import sys

sys.path.insert(0, "/workspace")

from engine import Engine
from reference import summarize, validate_row


def same(got, want):
    assert (got is None) == (want is None), (got, want)
    if want is None:
        return True
    assert set(got) == set(want)
    for k in ("n", "S", "Dx", "Dy"):
        assert type(got[k]) is int and got[k] == want[k], (k, got, want)
    if want["tau"] is None:
        assert got["tau"] is None
    else:
        assert math.isclose(got["tau"], want["tau"], rel_tol=1e-12, abs_tol=1e-12)
    return True


def diff_stream(W, rows, label):
    e = Engine(W)
    hist = []
    for t, row in enumerate(rows):
        saved = list(row)
        hist.append(validate_row(row))
        got = e.push(row)
        assert list(row) == saved, ("caller row mutated", label, t)
        if len(hist) < W:
            assert got is None, (label, t)
        else:
            want = summarize(hist[-W:])
            same(got, want)
    # Post-conditions on block structure invariants.
    B = 64
    blocks = e._blocks
    if e._n:
        for b in blocks:
            assert b.xs == sorted(b.xs)
            assert b.sy == sorted(b.ys)
            assert len(b.xs) == len(b.ys) == len(b.sy)
            assert b.xmax == b.xs[-1]
        assert sum(len(b.xs) for b in blocks) == e._n
        assert e._n == sum(e._cx.values()) == sum(e._cy.values())
    return len(hist)


def main():
    rng = random.Random(99173)
    widths = [1, 2, 3, 5, 7, 31, 63, 64, 65, 127, 128, 129, 200, 257, 513]
    total = 0

    # 1. Small alphabet (heavy ties, None on either axis).
    for W in widths:
        rows = [[rng.choice([None, -3, -1, 0, 0, 1, 1, 2]),
                 rng.choice([None, -3, -1, 0, 0, 1, 1, 2])] for _ in range(400)]
        total += diff_stream(W, rows, f"small-ties W={W}")

    # 2. Large-range integers (nearly all distinct), incl. big ints.
    for W in widths:
        rows = []
        for i in range(400):
            x = rng.randrange(-10 ** 30, 10 ** 30)
            y = rng.randrange(-10 ** 30, 10 ** 30)
            if i % 37 == 0:
                x = None
            if i % 41 == 0:
                y = None
            rows.append([x, y])
        total += diff_stream(W, rows, f"distinct W={W}")

    # 3. Constant points and fully-missing windows.
    for W in widths:
        rows = ([[7, 7]] * 100 + [[None, None]] * 100 +
                [[7, None], [None, 7]] * 50 + [[1, 2], [2, 1]] * 100)
        total += diff_stream(W, rows, f"constant-missing W={W}")

    # 4. Monotone up then down (max/min inversion swings).
    for W in (64, 128, 257):
        rows = [[i, i] for i in range(300)] + [[i, -i] for i in range(300)]
        total += diff_stream(W, rows, f"monotone W={W}")

    # 5. Repeated identical point sliding in/out (txy churn, block merges).
    for W in (1, 64, 130):
        rows = [[5, 5]] * 260 + [[5, 6]] * 260
        total += diff_stream(W, rows, f"dup-churn W={W}")

    # 6. Stress split/merge: width much larger than block size with ties.
    W = 900
    rows = [[rng.randrange(8), rng.randrange(8)] for _ in range(2500)]
    total += diff_stream(W, rows, "split-merge-stress")

    # 7. Invalid input must raise ValueError and not consume a window slot.
    e = Engine(3)
    e.push([1, 2])
    e.push([3, 4])
    for bad in ([1], [1, 2, 3], [True, 1], [1, True], [1.5, 2], ["1", 2],
                None, (1,), {1: 2}, [None, 1.0]):
        try:
            e.push(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(("accepted invalid row", bad))
    assert len(e._rows) == 2
    out = e.push([5, 6])  # now fills the 3-slot window
    same(out, summarize([(1, 2), (3, 4), (5, 6)]))
    for bad_w in (0, -1, True, 2.5, None, 1j):
        try:
            Engine(bad_w)
        except ValueError:
            pass
        else:
            raise AssertionError(("accepted invalid width", bad_w))

    # 8. tuple rows accepted too; independent returned dicts.
    e2 = Engine(2)
    assert e2.push((1, 2)) is None
    o1 = e2.push((2, 1))
    o2 = e2.push((3, 0))
    assert o1 is not o2
    same(o2, summarize([(2, 1), (3, 0)]))

    # 9. Long distinct stream: engine n equals width (no None) and exact match.
    W = 1024
    rows = [[i, (i * 1000003) % 2000007] for i in range(W + 700)]
    total += diff_stream(W, rows, "long-distinct")

    print(f"DIFFERENTIAL_OK rows_checked={total}")


if __name__ == "__main__":
    main()
