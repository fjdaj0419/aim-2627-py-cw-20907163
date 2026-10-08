# -*- coding: utf-8 -*-
"""旧版巡逻统计模块（2526 赛季遗留）—— Q7：昨天还能跑。

背景：本模块从上一届的巡逻系统原样迁移，上周还"能跑"。
最近的两次提交（见 git log）之后 CI 依旧全绿，但验收脚本报出的
数字不对，有的调用甚至卡死。上级只留了一句：昨天还能跑。

任务（题面 Q7·修复任务与提交物）：
1. 本模块共埋有 6 处 bug，其中两对互相遮蔽——修好 A 才会暴露 B；
2. 修复全部 6 处（验收以各函数 docstring 的契约为准，隐藏测试逐条核对）；
3. 在你的 README 里逐条写明：错在哪、你是怎么定位到的。

提示：不要迷信 git log 里的"修复"——有一件事被越修越错了。
"""

# ---------------------------------------------------------------------------
# 路线统计
# ---------------------------------------------------------------------------


def segment_length_cm(p1, p2):
    """两个检查点 (x, y) 之间的路线长度，单位：厘米。
    检查点坐标单位为格，1 格 = 1 米 = 100 厘米，路线按曼哈顿距离计算。"""
    return (abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])) * 100


def total_route_meters(points):
    """整条巡逻路线的长度，单位：米。
    points 为检查点序列 [(x, y), ...]，至少两个点。"""
    distance_in_meters = 0
    for i in range(len(points) - 1):
        # [Bug 1 修复] segment_length_cm 返回的是厘米，契约要求以"米"返回；
        # 旧实现漏除 100，导致结果整体放大 100 倍。
        distance_in_meters += segment_length_cm(points[i], points[i + 1]) / 100
    return distance_in_meters


# ---------------------------------------------------------------------------
# 事件日志
# ---------------------------------------------------------------------------
def parse_event(line):
    """解析一行事件日志，形如 "MOVE,3" / "SCAN,0" / "IDLE,1"。
    合法返回 {"type": str, "count": int}；脏行返回 None（不得抛异常）。"""
    parts = line.strip().split(",")
    if len(parts) != 2 or parts[0] not in ("MOVE", "SCAN", "IDLE"):
        return None
    if not parts[1].isdigit():
        return None
    return {"type": parts[0], "count": int(parts[1])}


def first_positive(samples):
    """返回样本序列中第一个正数；若没有正数，返回 None（上游约定）。"""
    for s in samples:
        if s > 0:
            return s
    return None


def calibrate(samples):
    """以第一个正样本为基线计算累计漂移：sum(s - baseline)。
    样本为空或没有正样本时，漂移为 0。"""
    baseline = first_positive(samples)
    # [Bug 2 修复] 当 samples 为空或全为非正数时，first_positive 返回 None；
    # 契约明确"漂移为 0"。若不守卫，下面的 `s - None` 会抛 TypeError，
    # 隐藏测试会直接覆盖这条路径（旧实现一遇空/全负样本就崩）。
    if baseline is None:
        return 0
    drift = 0
    for s in samples:
        drift += s - baseline
    return drift


def summarize_events(events, max_id):
    """统计 id 不超过 max_id 的事件。

    events: [{"id": int, "move": int, "samples": [int, ...]}, ...]
    每个事件的步数贡献 = move + calibrate(samples)。
    返回 {"events": 统计到的事件数, "steps": 步数总和}。
    """
    used = 0
    steps = 0
    for e in events:
        # [Bug 3 修复] 契约写"id 不超过 max_id"，即 ≤；旧实现 < 漏掉了
        # id == max_id 的事件。注意与 Bug 2 互为"遮蔽对"：不修这里，
        # 包含全负 samples 的事件不会被统计，bug 2 不会被触发；只修
        # 这里不修 bug 2，又会在含全负样本的事件上抛 TypeError。
        if e["id"] <= max_id:
            used += 1
            steps += e["move"] + calibrate(e["samples"])
    return {"events": used, "steps": steps}


def log(message, history=None):
    """向历史追加一条日志并返回整个历史列表。
    不显式传入 history 时，每次调用都从空历史开始。"""
    # [Bug 4 修复] 原形参 `history=[]` 是 Python 经典的"可变默认参数"陷阱：
    # 列表对象在函数定义时只创建一次，之后所有不传 history 的调用都会复用
    # 同一个列表，结果日志相互串味（log("a") 返回 ["a"]，再 log("b") 变
    # ["a","b"]）。契约要求"每次调用都从空历史开始"，这里改用 None 哨兵。
    if history is None:
        history = []
    history.append(message)
    return history


# ---------------------------------------------------------------------------
# 旧版巡逻模拟
# ---------------------------------------------------------------------------
def run_legacy_sim(rounds, stamina_start=100):
    """旧版巡逻模拟。

    契约（验收以本条为准）：
    - 依次执行第 0 .. rounds-1 轮，每轮基础消耗 8 点体力；
    - 第 4 轮起（轮号 >= 3）每轮额外消耗 5 点；
    - 任一轮结束后体力 <= 20 时立即终止，不再继续后面的轮；
    - trace 记录 (轮号, 该轮结束时的体力)；
    - 返回 {"rounds": 已执行轮数, "stamina": 剩余体力, "trace": trace}。
    """
    stamina = stamina_start
    round_ = 0
    trace = []
    while round_ < rounds:
        stamina -= 8
        if round_ >= 3:
            stamina -= 5
        trace.append((round_, stamina))
        # [Bug 5 修复] 契约"任一轮结束后体力 <= 20 时立即终止"。
        # 旧实现 `if stamina > 20: break` 把方向写反了，永远不会跳出。
        # 注意此 Bug 与下面的 Bug 6 互为"遮蔽对"：旧代码因 round_ 不
        # 自增，循环不会正常推进，所以"break 方向错"也不会无限跑；
        # 单独修任意一个都会立刻暴露另一个。
        if stamina <= 20:
            break
        # [Bug 6 修复] while 循环里 round_ 从未自增，跑到这里又一次会
        # 立刻因 `round_ < rounds` 永远成立而停不下来；只有当 Bug 5 的
        # break 命中时才会退出，所以旧实现任何调用都最多返回 1 轮。
        round_ += 1
    return {"rounds": len(trace), "stamina": stamina, "trace": trace}
