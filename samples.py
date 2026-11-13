WIDTH = 4
ROWS = [[1, 1], [1, 2], [2, 1], [None, 9], [2, 2], [2, 2]]
EXPECTED = [
    None, None, None,
    {"n": 3, "S": -1, "Dx": 2, "Dy": 2, "tau": -0.5},
    {"n": 3, "S": -1, "Dx": 2, "Dy": 2, "tau": -0.5},
    {"n": 3, "S": 0, "Dx": 0, "Dy": 2, "tau": None},
]
