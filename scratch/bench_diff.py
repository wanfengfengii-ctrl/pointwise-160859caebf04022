"""Per-window differential check on the exact frozen bench workloads.

Re-generates the identical streams bench.py uses (seed 761129, mixed/ties,
W in 2048/8192, length W+512) and compares EVERY window dict produced by the
optimized Engine against the retained reference.summarize on the raw window
rows.  The bench itself only compares an additive digest; this proves
window-by-window identity instead.
"""
import math
import random
import sys
from collections import deque

sys.path.insert(0, "/workspace")

from engine import Engine
from reference import summarize, validate_row

ADVANCES = 512
WIDTHS = (2048, 8192)
KINDS = ("mixed", "ties")


def workload(kind, W):
    rng = random.Random(761129)
    for i in range(W + ADVANCES):
        if kind == "mixed":
            x, y = rng.randrange(-10 ** 9, 10 ** 9), rng.randrange(-10 ** 9, 10 ** 9)
        else:
            x, y = rng.randrange(24), rng.randrange(24)
        yield [None if i % 29 == 0 else x, None if i % 43 == 0 else y]


def main():
    total_windows = 0
    for kind in KINDS:
        for W in WIDTHS:
            engine = Engine(W)
            ref_window = deque()
            rows = list(workload(kind, W))
            for t, row in enumerate(rows):
                got = engine.push(row)
                ref_window.append(validate_row(row))
                if len(ref_window) > W:
                    ref_window.popleft()
                if t < W - 1:
                    assert got is None, (kind, W, t)
                    continue
                want = summarize(ref_window)
                total_windows += 1
                # Exact integer statistics.
                for k in ("n", "S", "Dx", "Dy"):
                    assert type(got[k]) is int and got[k] == want[k], (kind, W, t, k, got, want)
                assert set(got) == set(want)
                if want["tau"] is None:
                    assert got["tau"] is None, (kind, W, t)
                else:
                    assert math.isclose(got["tau"], want["tau"], rel_tol=1e-12, abs_tol=1e-12), \
                        (kind, W, t, got["tau"], want["tau"])
    print(f"BENCH_WORKLOAD_DIFFERENTIAL_OK windows_compared={total_windows}")


if __name__ == "__main__":
    main()
