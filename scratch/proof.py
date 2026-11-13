import sys, random
sys.path.insert(0, "/workspace")
from reference import _inversions

# Reference inv = merge-sort inversions of y over points sorted by (x,y).
# For an unordered pair {a,b} with xa<xb it is counted iff ya>yb.
# When inserting p into set T, its pairs with q in T:
#   q left  (xq<xp): inversion iff yq>yp  -> lg
#   q right (xq>xp): inversion iff yp>yq i.e. yq<yp -> rl
# Ties on x never qualify (strict). So delta = lg + rl. Check with brute force.
rng = random.Random(1)
for trial in range(300):
    n = rng.randrange(1, 40)
    pts = [(rng.randrange(-5,6), rng.randrange(-5,6)) for _ in range(n)]
    # build inv incrementally (set semantics via list)
    inv = 0
    live = []
    for (x,y) in pts:
        lg = sum(1 for (a,b) in live if a<x and b>y)
        rl = sum(1 for (a,b) in live if a>x and b<y)
        inv += lg + rl
        live.append((x,y))
    ref = _inversions([y for x,y in sorted(pts)])
    assert inv == ref, (pts, inv, ref)
print("incremental inversion identity OK")

# Deletion identity: inv(p,T) = lg + rl measured within T including p? No:
# measured on T\\{p}. Removing p subtracts exactly its pairs with T\\{p}.
rng = random.Random(2)
for trial in range(300):
    n = rng.randrange(2, 40)
    pts = [(rng.randrange(-5,6), rng.randrange(-5,6)) for _ in range(n)]
    T = list(pts)
    total = _inversions([y for x,y in sorted(T)])
    for idx in range(n):
        x,y = T[idx]
        rest = T[:idx] + T[idx+1:]
        lg = sum(1 for (a,b) in rest if a<x and b>y)
        rl = sum(1 for (a,b) in rest if a>x and b<y)
        rest_inv = _inversions([b for a,b in sorted(rest)])
        assert total - rest_inv == lg + rl
    total = _inversions([y for x,y in sorted(T)])  # unchanged
print("deletion inversion identity OK")
