import json
from engine import Engine
from samples import WIDTH, ROWS

engine = Engine(WIDTH)
for row in ROWS:
    print(json.dumps({"input": row, "window": engine.push(row)}, ensure_ascii=False))
