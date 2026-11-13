import sys, gc, tracemalloc, random
sys.path.insert(0, "/workspace")
from engine import Engine

# Two engines, same window width but very different total stream lengths.
# Their retained state size must be essentially identical (bounded by W).
def drive(n, W, seed, ties):
    rng = random.Random(seed)
    e = Engine(W)
    for i in range(n):
        if ties:
            x, y = rng.randrange(24), rng.randrange(24)
        else:
            x, y = rng.randrange(10**9), rng.randrange(10**9)
        e.push([None if i % 29 == 0 else x, None if i % 43 == 0 else y])
    return e

gc.collect()
tracemalloc.start()
e_short = drive(2000, 512, 1, True)
gc.collect()
snap1 = tracemalloc.take_snapshot()
size1 = sum(s.size for s in snap1.statistics("filename") if "engine.py" in s.traceback[0].filename)
e_long = drive(60000, 512, 1, True)
gc.collect()
snap2 = tracemalloc.take_snapshot()
size2 = sum(s.size for s in snap2.statistics("filename") if "engine.py" in s.traceback[0].filename)
cur, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
# index content must equal window valid count regardless of stream length
n1 = sum(len(b.xs) for b in e_short._blocks)
n2 = sum(len(b.xs) for b in e_long._blocks)
print("engine.py retained bytes short:", size1, "long:", size2)
print("index points short:", n1, "long:", n2, "(both <= W=512)")
print("rows len:", len(e_short._rows), len(e_long._rows))
assert n1 <= 512 and n2 <= 512
assert len(e_short._rows) == len(e_long._rows) == 512
# long stream may hold at most a modest constant factor more (dict sizing),
# never linear in the 58000 extra rows.
assert size2 <= size1 * 3 + 4096, (size1, size2)
print("STATE_BOUND_OK")
