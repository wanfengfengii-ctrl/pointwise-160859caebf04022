"""Small independent pair oracle and bounded-stream regression."""
import gc
import math
import random
import sys
import tracemalloc
from engine import Engine
from reference import summarize
from samples import WIDTH, ROWS, EXPECTED


def oracle(rows):
    p = [r for r in rows if None not in r]
    s = dx = dy = 0
    for i, (x, y) in enumerate(p):
        for a, b in p[:i]:
            u = (x > a) - (x < a)
            v = (y > b) - (y < b)
            s += u * v
            dx += bool(u)
            dy += bool(v)
    return {"n": len(p), "S": s, "Dx": dx, "Dy": dy,
            "tau": s / math.sqrt(dx * dy) if dx and dy else None}


def same(got, want):
    assert (got is None) == (want is None), (got, want)
    if want is None:
        return
    assert set(got) == set(want), got
    for name in ("n", "S", "Dx", "Dy"):
        assert type(got[name]) is int and got[name] == want[name], (name, got, want)
    if want["tau"] is None:
        assert got["tau"] is None, got
    else:
        assert type(got["tau"]) in (int, float)
        assert math.isclose(got["tau"], want["tau"], rel_tol=1e-12, abs_tol=1e-12), (got, want)


def replay(W, rows):
    e = Engine(W)
    history = []
    for row in rows:
        saved = list(row)
        history.append(saved)
        want = oracle(history[-W:]) if len(history) >= W else None
        same(e.push(row), want)
        assert list(row) == saved
        if want is not None:
            same(summarize(history[-W:]), want)


def normal():
    e = Engine(WIDTH)
    for row, want in zip(ROWS, EXPECTED):
        same(e.push(row), want)
    assert Engine(10 ** 40).push([1, 2]) is None
    rng = random.Random(20261114)
    for w in (1, 2, 7, 31):
        rows = [[rng.choice([None, -2, -1, 0, 0, 1, 2]),
                 rng.choice([None, -2, -1, 0, 0, 1, 2])] for _ in range(240)]
        replay(w, rows)
    replay(9, [[i, i] for i in range(35)] + [[i, -i] for i in range(35)])
    replay(5, [[7, 7]] * 15 + [[None, None]] * 8)
    replay(3, [[10 ** 100, -10 ** 100], [0, 1], [-10 ** 100, 10 ** 100]] * 5)
    for w in (0, -1, True, 2.5, None):
        try:
            Engine(w)
        except ValueError:
            pass
        else:
            raise AssertionError(("invalid width", w))
    e = Engine(2)
    assert e.push([1, 2]) is None
    for row in ([1], [1, 2, 3], [True, 1], [1.5, 2], ["1", 2], None):
        try:
            e.push(row)
        except ValueError:
            pass
        else:
            raise AssertionError(("invalid row", row))
    same(e.push([2, 1]), oracle([[1, 2], [2, 1]]))
    print("NORMAL_REGRESSION_OK")


def stream():
    # Compare live Python allocations after a long stream, without retaining outputs.
    gc.collect()
    tracemalloc.start()
    e = Engine(64)
    def feed(begin, end):
        for i in range(begin, end):
            out = e.push([i, (i * 7919) % 104729])
            assert out is None or out["n"] == 64
    feed(0, 1000)
    gc.collect()
    before = tracemalloc.get_traced_memory()[0]
    feed(1000, 16000)
    gc.collect()
    after, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert after - before <= 2 * 1024 * 1024, (before, after)
    print("STREAM_REGRESSION_OK", {"live_growth": after - before, "peak": peak})


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
    if mode == "normal":
        normal()
    elif mode == "stream":
        stream()
    elif mode == "verify":
        normal()
        stream()
    else:
        raise SystemExit("use normal, stream or verify")
