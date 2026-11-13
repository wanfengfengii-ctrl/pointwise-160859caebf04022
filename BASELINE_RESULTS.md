# 基线实测

2026-11-14，使用随题完整 Python 源码，执行 checks.py verify、
三项 check_public.py 入口以及 bench.py target。
工作区只读，源码按同名模块编译到内存并执行对应 __main__ 入口；
这些脚本不读取外部文件，未声称已在工作区落盘。

正确性：NORMAL_REGRESSION_OK、STREAM_REGRESSION_OK。
长流检查：live_growth=56 bytes，peak=21428 bytes。
公开样例：PUBLIC_TIES_OK、PUBLIC_MISSING_OK、PUBLIC_INVALID_OK；
分别正常结束，三项脚本入口合计约 0.001009 秒。

完整性能复现退出 1，标记 PERFORMANCE_TARGET_NOT_MET。
以下为三轮中位耗时；Python 峰值为另一次完整处理的 tracemalloc 测量。

| 负载 | W | 参照秒 | 基线 Engine 秒 | Python 峰值 bytes |
| --- | ---: | ---: | ---: | ---: |
| mixed | 2048 | 2.395243 | 2.429938 | 250460 |
| mixed | 8192 | 11.111898 | 11.287147 | 1008332 |
| ties | 2048 | 1.983443 | 1.930426 | 186972 |
| ties | 8192 | 8.730538 | 8.539117 | 756852 |

每项产生 513 个窗口结果。目标为保持全部统计结果，
每项耗时不超过同进程参照的 1/5、每类大窗口耗时不超过小窗口的 3 倍，
且每项 Python 分配峰值不超过 64 MiB。
旧基线正确，未达标的业务原因是每个完整窗口重新排序和计数；
这里没有预设错误统计或依赖故障。绝对耗时仅供复核，以重跑的同机比值验收。
