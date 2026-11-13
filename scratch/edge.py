import sys
sys.path.insert(0, "/workspace")
from engine import Engine

# tuple compatibility and list/tuple both accepted
e = Engine(2)
assert e.push((1, 2)) is None
assert e.push([3, 4])["n"] == 2

# invalid before full window: no index build, slot not consumed
e = Engine(3)
e.push([1, 1])
for bad in ([1], [True, 1], [1, True], [1.5, 2], ["s", 2], None, (1,)):
    try:
        e.push(bad)
    except ValueError:
        continue
    raise AssertionError(("accepted", bad))
assert e._built is False and len(e._rows) == 1
# still can complete the window normally
assert e.push([2, 2]) is None
out = e.push([3, 3])
assert out["n"] == 3 and out["Dx"] == 3 and out["Dy"] == 3 and abs(out["tau"] - 1.0) < 1e-12

# bool width rejected even though bool is an int subclass
for w in (True, False):
    try:
        Engine(w)
    except ValueError:
        pass
    else:
        raise AssertionError(w)

# huge width
e = Engine(10 ** 40)
assert e.push([1, 2]) is None and e._built is False

# zero / negative width
for w in (0, -5):
    try:
        Engine(w)
    except ValueError:
        pass
    else:
        raise AssertionError(w)

# denominator zero -> tau None in several forms
e = Engine(2)
e.push([5, 1])
r = e.push([5, 2])  # x tied -> Dx=0
assert r == {"n": 2, "S": 0, "Dx": 0, "Dy": 1, "tau": None}, r
e = Engine(2)
e.push([1, 5]); r = e.push([2, 5])  # y tied -> Dy=0
assert r["Dy"] == 0 and r["Dx"] == 1 and r["tau"] is None

# window of only missing rows -> n=0, tau None
e = Engine(2)
e.push([None, 1]); r = e.push([2, None])
assert r == {"n": 0, "S": 0, "Dx": 0, "Dy": 0, "tau": None}, r
print("EDGE_OK")
