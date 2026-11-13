# 优化结果与可重跑实测

日期：2026-11-13。仅修改 `engine.py`；`reference.py`、`bench.py`、`checks.py`、
`check_public.py`、`samples.py` 全部保持原样（`git status` 仅显示 `engine.py`）。
仅使用 Python 标准库（`bisect`、`collections`），并复用参照的 `validate_row` /
`validate_width`，因此非法输入口径与基线完全一致。

## 1. 状态维护说明

目标是把逐窗重排改为增量维护。窗口里只有两坐标均非空的“有效点”参与统计，
含 `None` 的行仍占窗口位置但不进索引。引擎保留的全部状态大小都只随窗口宽度
`W` 增长，与已经处理过的总流长度无关：

| 状态 | 含义 | 每次 push 的更新 |
| --- | --- | --- |
| `_rows` (deque) | 最近 W 行（含缺失占位） | 右端 append，满窗左端 popleft |
| `_blocks` | 有效点的 sqrt 分块有序多重集 | 至多两块内增删 + 偶发 split/merge |
| `_cx` / `_cy` / `_cxy` | x 值、y 值、完整点的重数字典 | 各一次哈希读写 |
| `_n` | 有效点数 | 有效点 +1 / -1 |
| `_tx` `_ty` `_txy` | 三轴并列对数 ΣC2(重数) | 随字典重数增量 |
| `_inv` | 严格逆序对数（两轴都不同且顺序相反） | 一次象限计数的增量 |

### 分块索引

每个块持有按 x 升序的并行 `xs`/`ys`，外加该块 y 的排序副本 `sy` 和 `xmax`。
块间按 x 有序，块容量维持在 `B//2 … 2B`（`B=192`）：插入超过 `2B` 就二分，
删除低于 `B//2` 且能与单个邻居在 `2B` 内合并时才合并。块数与块长都是
`O(sqrt(n))`，且任何时刻需要逐点扫描的“跨步块”至多两个（同 x 运行段最多
跨一块边界）；其余整块用 `bisect` 在 `sy` 上做 C 级二分。

二维象限计数 `_quadrants(x, y)` 返回 `(ll, lg, rl, rg)`，分别是
`x'<x,y'<y`、`x'<x,y'>y`、`x'>x,y'<y`、`x'>x,y'>y` 的点数；同 x 或同 y
在对应轴上不计入。

### 逆序数与统计口径

记 `pairs = C2(n)`。参照实现先按 `(x,y)` 排序再求 y 的严格逆序数 `inv`，
并有 `S = pairs - tx - ty + txy - 2·inv`、`Dx = pairs - tx`、
`Dy = pairs - ty`。增量地：

- 插入点 p 时，它与已有点新形成的逆序对 = 左上方 `lg` + 右下方 `rl`
  （两种方向相反的点对，严格不等，并列不计），`_inv += lg + rl`；
- 删除点 p 时，在“不含 p”的当前集合上取同样的 `lg + rl`，
  `_inv -= lg + rl`；删除先于插入执行，象限计数天然不含正在更替的点。

这两条恒等式已用暴力枚举在数百组随机多重集上证明（`scratch/proof.py`）。
并列点的滑入滑出通过字典重数精确维护：加入第 k 个副本时对应 C2 增加 k-1，
删除时减去剩余重数；完全相同点的重数由 `_cxy` 保留。

### 首次成窗与约束符合性

- 前 W-1 次 push 只入 deque、返回 `None`；第 W 次一次性全量建索引
  （排序分块 + 三轴重数字典 + 压缩 y 秩上的 Fenwick 树求初始 `inv`），
  之后每个窗口纯增量。
- 不存在逐窗排序，也不扫描全部有效点：稳态每次 push 仅做 `O(sqrt(W))`
  的二分与至多两块的逐点扫描，以及常数次字典操作。
- 输入单遍消费，一次 `push` 恰好消费一行；不预读未来行，不保留全流坐标
  字典或累计历史（已由 `scratch/growth.py` 证明长流后保留内存不随流长度
  线性增长）。
- `n/S/Dx/Dy` 全程是精确 Python int，无浮点累计；仅 `tau` 用一次
  `math.sqrt`，分母 `Dx*Dy==0` 时返回 `None`，与参照逐位同口径。
- 非法输入在 `validate_row`/`validate_width` 处抛 `ValueError`，发生在任何
  状态变更之前，故不消费窗口、也不修改调用方行（内部存的是 tuple 副本）。

## 2. 差分验证（证明结果未变，而非只看摘要）

基准 `bench.py` 只核对累加 digest。另做了逐窗差分：

- `scratch/bench_diff.py`：用与 `bench.py` 完全相同的固定种子 761129 重放
  mixed/ties × W=2048/8192 四条流，对全部 **2052 个窗口**逐窗比较
  `Engine.push` 与 `reference.summarize(原始窗口行)`：四个整数统计精确相等、
  `tau` 在 1e-12 内、`None` 语义一致。
- `scratch/diff_check.py`：15 种窗口宽度（含 1、块边界 63/64/65、127/128/129
  等）× 重并列/大整数/常量/全缺失/单调/副本抖动/900 宽分裂合并压力流，
  共 27084 行逐窗差分，并校验块结构不变量、调用方行不被修改、非法输入不
  占槽、tuple/list 兼容、返回字典互相独立。
- `scratch/adversarial.py`：6000 行重 ties 长流（反复 split/merge）、全缺失
  后恢复、有效/缺失交替、全等点与异点交替、10^200 级大整数、宽 1 与超宽
  窗口等退化场景，逐窗差分 + 块与字典不变量。
- `scratch/proof.py`：逆序数插入/删除增量恒等式的暴力证明。

## 3. 可重跑实测结果

入口与 CONTRACT.md 一致，仓库根目录执行：

```
python3 checks.py verify
python3 check_public.py ties
python3 check_public.py missing
python3 check_public.py invalid
python3 bench.py target
python3 -I scratch/bench_diff.py
python3 -I scratch/diff_check.py
python3 -I scratch/adversarial.py
```

正确性：`NORMAL_REGRESSION_OK`、`STREAM_REGRESSION_OK`
（live_growth=64 B，peak=38520 B）、`PUBLIC_TIES_OK`、`PUBLIC_MISSING_OK`、
`PUBLIC_INVALID_OK`、`BENCH_WORKLOAD_DIFFERENTIAL_OK windows_compared=2052`、
`DIFFERENTIAL_OK rows_checked=27084`、`ADVERSARIAL_OK`、`EDGE_OK`。

`python3 bench.py target` 连续三轮（同进程三轮中位数，单位秒；峰值为
tracemalloc 另测的 Python 分配）：

| 负载 | W | 参照秒(区间) | Engine 秒(区间) | 提速 | 峰值 bytes | 64 MiB |
| --- | ---: | --- | --- | ---: | ---: | --- |
| mixed | 2048 | 1.495–1.535 | 0.0162–0.0179 | ~85–94× | 693,384 | 通过 |
| mixed | 8192 | 7.52–7.66 | 0.0380–0.0408 | ~185–200× | 2,819,296 | 通过 |
| ties | 2048 | 1.205–1.212 | 0.0165–0.0173 | ~70–73× | 363,296 | 通过 |
| ties | 8192 | 5.46–5.67 | 0.0388–0.0393 | ~140–146× | 1,321,304 | 通过 |

门槛核对（三轮均输出 `PERFORMANCE_TARGET_OK`，退出 0）：

- 每项 Engine 中位数 ≤ 参照 1/5：实际约为参照的 1/70 到 1/200，远超要求。
- 每类 W=8192 中位数 ≤ 3 × W=2048：实测 mixed ≈ 2.2–2.5×，ties ≈ 2.3–2.4×。
- 每项 Python 分配峰值 ≤ 64 MiB：最大 2,819,296 B ≈ 2.69 MiB。

块大小 `B=192` 的依据（`scratch/tune_block.py` 实测扫描）：在本负载下把
块数压到约 W/192，使每次象限计数的 `bisect` 次数下降，同时逐点扫描仍限于
至多两个块；相比 B=64，W 从 2048 增至 8192 的耗时比从 ~3.2 降到 ~2.4，
稳定低于 3 倍门槛且总耗时更短。复杂度仍为每次 push `O(sqrt(W))`。
