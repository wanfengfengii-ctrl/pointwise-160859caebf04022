"""Correct independent-window Kendall tau-b reference; no rolling index."""
from collections import Counter
from math import sqrt


def validate_width(width):
    if type(width) is not int or width < 1:
        raise ValueError("width must be a positive integer")
    return width


def validate_row(row):
    if not isinstance(row, (list, tuple)) or len(row) != 2:
        raise ValueError("row must contain two coordinates")
    if any(v is not None and type(v) is not int for v in row):
        raise ValueError("coordinates must be integers or null")
    return tuple(row)


def _choose2(k):
    return k * (k - 1) // 2


def _inversions(values):
    size = len(values)
    src = list(values)
    dst = [0] * size
    count = 0
    step = 1
    while step < size:
        for lo in range(0, size, step * 2):
            mid = min(lo + step, size)
            hi = min(lo + step * 2, size)
            i, j, out = lo, mid, lo
            while i < mid and j < hi:
                if src[i] <= src[j]:
                    dst[out] = src[i]
                    i += 1
                else:
                    dst[out] = src[j]
                    j += 1
                    count += mid - i
                out += 1
            while i < mid:
                dst[out] = src[i]
                out += 1
                i += 1
            while j < hi:
                dst[out] = src[j]
                out += 1
                j += 1
        src, dst = dst, src
        step *= 2
    return count


def summarize(rows):
    points = sorted((x, y) for x, y in rows if x is not None and y is not None)
    n = len(points)
    pairs = _choose2(n)
    tx = sum(_choose2(k) for k in Counter(x for x, y in points).values())
    ty = sum(_choose2(k) for k in Counter(y for x, y in points).values())
    txy = sum(_choose2(k) for k in Counter(points).values())
    s = pairs - tx - ty + txy - 2 * _inversions([y for x, y in points])
    dx, dy = pairs - tx, pairs - ty
    return {"n": n, "S": s, "Dx": dx, "Dy": dy,
            "tau": s / sqrt(dx * dy) if dx and dy else None}
