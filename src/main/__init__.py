# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    if hp < 0:
        return 0
    if hp > max_hp:
        return 100
    return int(hp / max_hp * 100)
    raise NotImplementedError("Q1 hp_ratio：题面 Q1·血量百分比与精度保障")


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    #电量修正
    def battery_fix(battery):
        if battery < 0:
            return 0
        if battery > 100:
            return 100
        raise NotImplementedError()
    
    hp_ratio = hp_ratio(hp)
    battery_ratio = battery_fix(int(battery))
    
    if battery_ratio >= 80:
        battery_status = "OK"
    elif battery_ratio >= 40:
        battery_status = "WARNING"
    else:
        battery_status = "LOW"
    return f"{name:<10}|{robot_type:^10}|HP {hp_ratio:>3}%|BAT {battery_ratio:>3}%|{battery_status}"

    #raise NotImplementedError("Q1 status_report：题面 Q1·电量映射与报告格式")


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
def analyze_damage_log(lines):
    """解析混合格式伤害日志，返回固定契约的统计 dict。

    支持两种有效行：
      - 传感器行: "F:32,L:5,R:12"  (F→front, L→left, R→right，段可缺失)
      - JSON 行:  '{"armor":"front","damage":30,"id":7}'  (id 可选)
    其余行（空行 / #注释 / 格式非法）一律跳过，全程不抛异常。
    """
    # ---- 统计变量初始化 ----
    total = 0                          # 有效事件伤害总和
    by_armor = {"front": 0, "left": 0, "right": 0}  # 三部位桶，恒存在
    event_count = 0                    # 有效事件计数（用于算 avg）
    seen_ids = set()                   # 已出现的 JSON id，用于去重

    # 传感器字母 → 部位名映射
    SENSOR_MAP = {"F": "front", "L": "left", "R": "right"}

    for line in lines:
        try:
            stripped = line.strip()

            # ---- 跳过空行和 # 注释 ----
            if stripped == "" or stripped.startswith("#"):
                continue

            # ============================================================
            # 尝试 JSON 行解析
            # ============================================================
            if stripped.startswith("{"):
                data = json.loads(stripped)          # 非法 JSON → except 跳过

                # 校验 armor：必须是三部位之一
                armor = data.get("armor")
                if armor not in ("front", "left", "right"):
                    continue

                # 校验 damage：必须是严格正整数（排除 bool / float / 0 / 负数）
                damage = data.get("damage")
                if isinstance(damage, bool) or not isinstance(damage, int) or damage <= 0:
                    continue

                # id 去重：有 id 且重复 → 跳过；首次出现 → 记录
                if "id" in data:
                    eid = data["id"]
                    if eid in seen_ids:
                        continue
                    seen_ids.add(eid)

                # 计入统计
                total = total + damage
                # 记录每一个部位的伤害值
                by_armor[armor] += damage# 记录每一个部位的伤害值
                event_count += 1

            # ============================================================
            # 尝试传感器行解析: "F:32,L:5,R:12"
            # ============================================================
            else:
                segments = stripped.split(",")
                events = []               # 本行解析出的 (armor, damage) 列表
                valid = True

                for seg in segments:
                    seg = seg.strip()
                    # 每段必须恰好含一个 ':'
                    if ":" not in seg:
                        valid = False
                        break
                    parts = seg.split(":")
                    if len(parts) != 2:
                        valid = False
                        break

                    letter, val_str = parts[0].strip(), parts[1].strip()

                    # 字母必须是 F / L / R 之一
                    if letter not in SENSOR_MAP:
                        valid = False
                        break

                    # 值必须是正整数（> 0）
                    try:
                        val = int(val_str)
                    except ValueError:
                        valid = False
                        break
                    if val <= 0:
                        valid = False
                        break

                    events.append((SENSOR_MAP[letter], val))

                # 全部段合法 且 至少有一段 → 计入统计
                if valid and events:
                    for armor, damage in events:
                        total += damage
                        by_armor[armor] += damage
                        event_count += 1

        except Exception:
            # 任何未预料的异常 → 当脏行跳过，绝不向外抛出
            continue

    # ---- 计算 most_hit 和 avg ----
    if event_count == 0:
        most_hit = None
        avg = 0.0
    else:
        # 受击伤害最大的部位（dict 插入序固定，max 返回第一个最大值）
        most_hit = max(by_armor, key=lambda k: by_armor[k])
        avg = round(total / event_count, 2)

    return {
        "total": total,
        "by_armor": by_armor,
        "most_hit": most_hit,
        "avg": avg,
    }


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """TODO(Q3)：位置 setter；三重输入校验见题面 Q3 规范第 1 条。"""
        raise NotImplementedError("Q3 current_pos.setter：题面 Q3·位置校验三步")

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        raise NotImplementedError("Q3 move_forward：题面 Q3·前进、碰撞与断电")

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        raise NotImplementedError("Q3 turn_left")

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        raise NotImplementedError("Q3 turn_right")


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    raise NotImplementedError("Q4 next_step_toward：题面 Q4·贪心策略与回退")


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    raise NotImplementedError("Q5 decide：题面 Q5·决策规则表 R1-R7")


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    raise NotImplementedError("Q6 run_patrol：题面 Q6·主循环与统计契约")


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    raise NotImplementedError("Q6 report_to_json：题面 Q6·报告序列化")


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    raise NotImplementedError("Bonus bfs_path_length")


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
