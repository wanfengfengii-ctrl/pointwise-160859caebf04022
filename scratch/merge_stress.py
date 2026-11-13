import sys, random
sys.path.insert(0, "/workspace")
from engine import Engine
from reference import summarize

# Force many block merges: fill window then stream a different-distribution
# sequence so blocks repeatedly shrink below B//2 and merge.
rng = random.Random(31337)
W = 1000
e = Engine(W)
hist = []
# phase 1: only two x values -> few distinct, then phase 2: wide distinct x
for i in range(W + 1500):
    if i < W:
        row = [rng.randrange(3), rng.randrange(100000)]
    else:
        row = [rng.randrange(100000), rng.randrange(100000)]
    hist.append(tuple(row))
    out = e.push(row)
    if i >= W - 1:
        want = summarize(hist[-W:])
        for k in ("n","S","Dx","Dy"):
            assert out[k] == want[k], (i,k,out,want)
        # parallel-array integrity after every possible merge
        for b in e._blocks:
            assert b.xs == sorted(b.xs)
            assert b.sy == sorted(b.ys)
            assert all(isinstance(v, int) for v in b.xs + b.ys)
print("MERGE_STRESS_OK")

# Deterministic shrink-to-empty then regrow, exercising empty-block deletion.
e = Engine(300)
for i in range(300):
    e.push([i, i])
assert sum(len(b.xs) for b in e._blocks) == 300
for i in range(300):
    e.push([None, None])
assert e._blocks == [] and e._n == 0
for i in range(300):
    out = e.push([i, -i])
assert sum(len(b.xs) for b in e._blocks) == 300 and e._n == 300
print("EMPTY_REGROW_OK")
