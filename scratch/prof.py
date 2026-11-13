import sys, random, cProfile, pstats, io
sys.path.insert(0, "/workspace")
from engine import Engine

def gen(kind, W):
    rng = random.Random(761129)
    out=[]
    for i in range(W + 512):
        if kind == "mixed":
            x, y = rng.randrange(-10**9, 10**9), rng.randrange(-10**9, 10**9)
        else:
            x, y = rng.randrange(24), rng.randrange(24)
        out.append((None if i % 29 == 0 else x, None if i % 43 == 0 else y))
    return out

W=8192
for kind in ("mixed","ties"):
    rows = gen(kind, W)
    pr = cProfile.Profile()
    e = Engine(W)
    pr.enable()
    for r in rows:
        e.push(r)
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("tottime")
    ps.print_stats(12)
    print("==== ",kind)
    print(s.getvalue())
