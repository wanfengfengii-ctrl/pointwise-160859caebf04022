import sys, time, random
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

for W in (2048, 8192):
    rows = gen("mixed", W)
    # time warmup build separately
    e = Engine(W)
    t0=time.perf_counter()
    for r in rows[:W]:
        e.push(r)
    t1=time.perf_counter()
    for r in rows[W:]:
        e.push(r)
    t2=time.perf_counter()
    print(f"W={W} build(first window)={t1-t0:.4f}s  512 advances={t2-t1:.4f}s  total={t2-t0:.4f}s")
