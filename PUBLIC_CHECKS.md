# 可选公开小样例

从仓库根目录可分别运行：
- python3 check_public.py ties
- python3 check_public.py missing
- python3 check_public.py invalid

旧基线三项均应退出 0，分别输出 PUBLIC_TIES_OK、PUBLIC_MISSING_OK、
PUBLIC_INVALID_OK；没有预期业务失败，性能优化不会改变这些正确结果。
脚本只调用公开 Engine(W).push，使用极小输入及明确整数统计预期。
覆盖单轴并列随窗口滑出、缺失占位与常量/空有效窗口、
以及非法 bool 坐标拒绝后窗口不被消费；三项合计应在 120 秒内结束。
这些样例不覆盖索引策略、长流资源、全部合法整数或性能门槛；
全部通过仅代表有限样例通过，不能替代原回归及完整验收。

缺少公开接口时报告 PUBLIC_INTERFACE_NOT_IMPLEMENTED；其他导入或运行异常不当作业务断言失败。

非空 tau 沿用 CONTRACT.md 的绝对或相对误差 1e-12；整数统计及 None 仍精确核对。
