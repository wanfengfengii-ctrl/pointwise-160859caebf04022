"""Compatible, correct baseline. The optimization belongs in this module."""
from collections import deque
from reference import summarize, validate_row, validate_width


class Engine:
    def __init__(self, W):
        self.W = validate_width(W)
        self._rows = deque()

    def push(self, row):
        point = validate_row(row)
        self._rows.append(point)
        if len(self._rows) > self.W:
            self._rows.popleft()
        if len(self._rows) < self.W:
            return None
        return summarize(self._rows)
