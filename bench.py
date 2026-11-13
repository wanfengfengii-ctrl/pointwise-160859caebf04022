"""Frozen workload; compare full construction + all pushes, excluding generation."""
import gc
import json
import random
import statistics
import sys
import time
import tracemalloc
from collections import deque
from engine import Engine
from reference import summarize, validate_width, validate_row

WIDTHS = (2048, 8192)
ADVANCES = 512
KINDS = ("mixed", "ties")


class Reference:
    def __init__(self, W):
        self.W = validate_width(W)
        self.rows = deque()

    def push(self, row):
        self.rows.append(validate_row(row))
        if len(self.rows) > self.W:
            self.rows.popleft()
        return summarize(self.rows) if len(self.rows) == self.W else None


def workload(kind, W):
    rng = random.Random(761129)
    for i in range(W + ADVANCES):
        if kind == "mixed":
            x, y = rng.randrange(-10**9, 10**9), rng.randrange(-10**9, 10**9)
        else:
            x, y = rng.randrange(24), rng.randrange(24)
        yield [None if i % 29 == 0 else x, None if i % 43 == 0 else y]


def consume(factory, W, rows):
    e = factory(W)
    digest = [0, 0, 0, 0, 0]
    for row in iter(rows):
        out = e.push(row)
        if out is not None:
            digest[0] += 1
            for j, key in enumerate(("n", "S", "Dx", "Dy"), 1):
                digest[j] += out[key]
    return digest


def timed(factory, W, rows):
    gc.collect()
    start = time.perf_counter()
    digest = consume(factory, W, rows)
    return time.perf_counter() - start, digest


def main(target=False):
    report = {}
    for kind in KINDS:
        results = {}
        for W in WIDTHS:
            rows = tuple(tuple(r) for r in workload(kind, W))
            a, b = [], []
            expected = None
            for trial in range(3):
                order = (Reference, Engine) if trial % 2 == 0 else (Engine, Reference)
                for factory in order:
                    elapsed, digest = timed(factory, W, rows)
                    if expected is None:
                        expected = digest
                    assert digest == expected, (kind, W, digest, expected)
                    (a if factory is Reference else b).append(elapsed)
            gc.collect()
            tracemalloc.start()
            measured = consume(Engine, W, rows)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            assert measured == expected
            results[str(W)] = {"reference_s": statistics.median(a),
                               "engine_s": statistics.median(b),
                               "python_peak_bytes": peak,
                               "digest": expected}
            print(json.dumps({"kind": kind, "W": W, **results[str(W)]}), flush=True)
        report[kind] = results
    passed = True
    for results in report.values():
        for r in results.values():
            passed &= r["engine_s"] <= r["reference_s"] / 5
            passed &= r["python_peak_bytes"] <= 64 * 1024 * 1024
        passed &= results["8192"]["engine_s"] <= 3 * results["2048"]["engine_s"]
    print("PERFORMANCE_TARGET_OK" if passed else "PERFORMANCE_TARGET_NOT_MET")
    if target and not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main(len(sys.argv) > 1 and sys.argv[1] == "target")
