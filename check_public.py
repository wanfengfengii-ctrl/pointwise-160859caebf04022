"""Tiny observable behavior cases, deliberately not a performance judge."""
import sys
import math
try:
    import engine
except ModuleNotFoundError as exc:
    if exc.name == "engine":
        raise SystemExit("PUBLIC_INTERFACE_NOT_IMPLEMENTED: engine")
    raise


def new_engine(W):
    cls = getattr(engine, "Engine", None)
    if not callable(cls):
        raise SystemExit("PUBLIC_INTERFACE_NOT_IMPLEMENTED: Engine")
    instance = cls(W)
    if not callable(getattr(instance, "push", None)):
        raise SystemExit("PUBLIC_INTERFACE_NOT_IMPLEMENTED: Engine.push")
    return instance


def emit(W, rows):
    instance = new_engine(W)
    return [instance.push(row) for row in rows]



def assert_outputs(actual, expected):
    assert len(actual) == len(expected), actual
    for got, want in zip(actual, expected):
        if want is None:
            assert got is None, got
            continue
        assert isinstance(got, dict) and set(got) == set(want), got
        for key in ("n", "S", "Dx", "Dy"):
            assert type(got[key]) is int and got[key] == want[key], (key, got)
        if want["tau"] is None:
            assert got["tau"] is None, got
        else:
            assert type(got["tau"]) in (int, float) and math.isclose(
                got["tau"], want["tau"], rel_tol=1e-12, abs_tol=1e-12), got


def ties():
    got = emit(4, [[1, 1], [1, 2], [2, 1], [None, 9], [3, 3]])
    expected = [None, None, None,
                   {"n": 3, "S": -1, "Dx": 2, "Dy": 2, "tau": -0.5},
                   {"n": 3, "S": 1, "Dx": 3, "Dy": 3, "tau": 1 / 3}]
    assert_outputs(got, expected)


def missing():
    got = emit(3, [[4, 1], [4, 2], [4, 2], [None, 3], [None, None], [7, None]])
    expected = [None, None,
                   {"n": 3, "S": 0, "Dx": 0, "Dy": 2, "tau": None},
                   {"n": 2, "S": 0, "Dx": 0, "Dy": 0, "tau": None},
                   {"n": 1, "S": 0, "Dx": 0, "Dy": 0, "tau": None},
                   {"n": 0, "S": 0, "Dx": 0, "Dy": 0, "tau": None}]
    assert_outputs(got, expected)


def invalid():
    e = new_engine(2)
    assert e.push([1, 2]) is None
    try:
        e.push([True, 9])
    except ValueError:
        pass
    else:
        raise AssertionError("invalid input was accepted")
    assert_outputs([e.push([2, 1])], [{"n": 2, "S": -1, "Dx": 1, "Dy": 1, "tau": -1.0}])


if __name__ == "__main__":
    name = sys.argv[1]
    case = {"ties": ties, "missing": missing, "invalid": invalid}.get(name)
    if case is None:
        raise SystemExit("use ties, missing or invalid")
    try:
        case()
    except AssertionError as exc:
        print("PUBLIC_" + name.upper() + "_FAIL", str(exc))
        raise SystemExit(1)
    print("PUBLIC_" + name.upper() + "_OK")
