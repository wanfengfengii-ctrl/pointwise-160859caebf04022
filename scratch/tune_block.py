import sys, time, random, statistics
sys.path.insert(0, "/workspace")
import engine

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

for B in (32, 48, 64, 96, 128, 192, 256):
    engine._BLOCK = B
    res = {}
    for kind in ("mixed","ties"):
        for W in (2048, 8192):
            rows = gen(kind, W)
            ts=[]
            for _ in range(3):
                e = engine.Engine(W)
                t0=time.perf_counter()
                for r in rows: e.push(r)
                ts.append(time.perf_counter()-t0)
            res[(kind,W)] = statistics.median(ts)
    ratio_m = res[("mixed",8192)]/res[("mixed",2048)]
    ratio_t = res[("ties",8192)]/res[("ties",2048)]
    print(f"B={B:4d} mixed2k={res[('mixed',2048)]:.4f} mixed8k={res[('mixed',8192)]:.4f} x{ratio_m:.2f}"
          f" | ties2k={res[('ties',2048)]:.4f} ties8k={res[('ties',8192)]:.4f} x{ratio_t:.2f}")
