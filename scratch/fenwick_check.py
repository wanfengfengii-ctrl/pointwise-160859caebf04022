import sys, random
sys.path.insert(0, "/workspace")
from engine import Engine
from reference import _inversions, summarize

# Independently verify _build_index's inv against reference merge-sort inv
# across many first-window builds (this is the only path that uses Fenwick).
rng = random.Random(2025)
for trial in range(200):
    W = rng.randrange(1, 300)
    rows = []
    for i in range(W):
        x = None if rng.random() < 0.2 else rng.randrange(-4, 5)
        y = None if rng.random() < 0.2 else rng.randrange(-4, 5)
        rows.append([x, y])
    e = Engine(W)
    out = None
    for r in rows:
        out = e.push(r)
    pts = sorted((x, y) for x, y in rows if x is not None and y is not None)
    ref_inv = _inversions([y for x, y in pts])
    assert e._inv == ref_inv, (W, e._inv, ref_inv)
    # full summary cross-check
    rs = summarize([tuple(r) for r in rows])
    for k in ("n","S","Dx","Dy"):
        assert out[k] == rs[k], (k, out, rs)
    assert (out["tau"] is None) == (rs["tau"] is None)
print("FENWICK_BUILD_OK over 200 first-window builds")
