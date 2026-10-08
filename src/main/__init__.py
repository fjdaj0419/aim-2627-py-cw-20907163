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
    """血量百分比，返回 0-100 的 int。

    规则：
    - hp < 0 时返回 0（负血量截断）
    - hp > max_hp 时返回 100（超量截断）
    - 否则返回 int(hp / max_hp * 100)，向下取整
    """
    if hp < 0:
        return 0
    if hp > max_hp:
        return 100
    return int(hp / max_hp * 100)


def status_report(name, robot_type, hp, max_hp, battery):
    """生成一行自检报告字符串。

    格式：{name:<10}|{robot_type:^10}|HP {百分比:>3}%|BAT {电量:>3}%|{档位}
    - 名称左对齐占 10 字符
    - 机型居中占 10 字符
    - 血量百分比右对齐占 3 字符
    - 电量百分比右对齐占 3 字符
    - 档位：OK (≥75) / WARNING (≥30) / LOW (<30)
    """
    # 电量修正：截断到 0-100 范围
    def battery_fix(battery):
        if battery < 0:
            return 0
        if battery > 100:
            return 100
        return battery

    hp_pct = hp_ratio(hp, max_hp)
    battery_ratio = battery_fix(int(battery))

    # 电量档位判定
    if battery_ratio >= 75:
        battery_status = "OK"
    elif battery_ratio >= 30:
        battery_status = "WARNING"
    else:
        battery_status = "LOW"

    return f"{name:<10}|{robot_type:^10}|HP {hp_pct:>3}%|BAT {battery_ratio:>3}%|{battery_status}"


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
                by_armor[armor] += damage  # 记录每一个部位的伤害值
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
        """位置 setter：三重输入校验。"""
        # 第一步：类型校验——只接受 tuple 或 list
        if not isinstance(value, (tuple, list)):
            raise TypeError("current_pos 必须是 tuple 或 list")
        # 第二步：长度校验——必须恰好包含 2 个元素
        if len(value) != 2:
            raise TypeError("current_pos 必须是长度为 2 的 tuple 或 list")
        # 第三步：元素规范化——转为 int 并夹回地图范围，最后存为 tuple
        self._pos = self._clamp_cell(value)

    def move_forward(self):
        """朝当前 facing 前进一格，返回执行后的位置。"""
        # 检查电量：≤ 0 时底盘断电，不产生位移
        if self._fuel <= 0:
            return self._pos
        # 计算前方格子坐标：当前坐标 + 朝向的单位位移向量
        dx, dy = self._facing.delta
        next_x = self._pos[0] + dx
        next_y = self._pos[1] + dy
        # 判断前方格子是否为障碍或越界
        if self.is_blocked(next_x, next_y):
            # 碰撞：位置不变、朝向不变、碰撞计数加 1
            self._collision_count += 1
        else:
            # 可通行：移动到前方格子
            self._pos = (next_x, next_y)
        # 前进消耗 1 单位电量（无论是否碰撞）
        self._fuel -= 1
        # 返回执行后的当前位置
        return self._pos

    def turn_left(self):
        """原地左转 90°（逆时针），返回新的 Facing。"""
        # 定义左转映射：当前朝向 → 左转后的朝向
        left_map = {
            Facing.UP: Facing.LEFT,    # 上 → 左
            Facing.LEFT: Facing.DOWN,  # 左 → 下
            Facing.DOWN: Facing.RIGHT,  # 下 → 右
            Facing.RIGHT: Facing.UP,   # 右 → 上
        }
        # 更新朝向
        self._facing = left_map[self._facing]
        # 返回新的朝向
        return self._facing

    def turn_right(self):
        """原地右转 90°（顺时针），返回新的 Facing。"""
        # 定义右转映射：当前朝向 → 右转后的朝向
        right_map = {
            Facing.UP: Facing.RIGHT,    # 上 → 右
            Facing.RIGHT: Facing.DOWN,  # 右 → 下
            Facing.DOWN: Facing.LEFT,   # 下 → 左
            Facing.LEFT: Facing.UP,     # 左 → 上
        }
        # 更新朝向
        self._facing = right_map[self._facing]
        # 返回新的朝向
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """贪心导航：返回下一步应朝向的 Facing（题面 Q4 规范 1-3）。

    核心思想：只在"能让曼哈顿距离严格变小"的方向里挑一个走。
    规则回顾：
      1. 候选方向 = 四邻域中，相邻格不是障碍 **且** 移动后到目标曼哈顿
         距离严格变小的方向（持平不算候选）。
      2. 有多个候选时，先走与目标绝对坐标差较大的那条轴。
      3. 一个候选都没有时，原地保持 current_facing。
      4. 不管地图边界（越界由 SentryGrid.move_forward 处理）。
    """
    # ---- 第 0 步：拆坐标，算出当前位置到目标的曼哈顿距离 ----
    x, y = int(pos[0]), int(pos[1])       # 当前位置
    tx, ty = int(target[0]), int(target[1])  # 目标位置
    cur_dist = abs(x - tx) + abs(y - ty)  # 当前曼哈顿距离（基准值）

    # ---- 第 1 步：枚举四邻域，收集所有合法候选方向 ----
    candidates = []                       # 存本步可选的 Facing
    for f in Facing:                      # 遍历 UP / DOWN / LEFT / RIGHT
        dx, dy = f.delta                  # 该朝向的单位位移 (dx, dy)
        nx, ny = x + dx, y + dy           # 走一步后的相邻格坐标
        # 条件 A：相邻格不是障碍（注意：这里不判断是否越界，见规范 4）
        if (nx, ny) in obstacles:
            continue
        # 条件 B：移动后到目标的曼哈顿距离要"严格变小"
        new_dist = abs(nx - tx) + abs(ny - ty)
        if new_dist < cur_dist:           # 持平（==）不算候选
            candidates.append(f)

    # ---- 第 2 步：没有候选 → 回退为保持当前朝向（规范 3）----
    if not candidates:
        return current_facing

    # 只有一个候选，直接走它
    if len(candidates) == 1:
        return candidates[0]

    # ---- 第 3 步：多个候选 → 平局打破（规范 2）----
    # 关键事实：每个轴（x / y）上至多只有一个方向能"严格减小距离"
    #   （朝目标去的那一侧减小，背目标的那一侧增大），
    # 所以两个候选必然一横一纵，最多就这两个。
    dx_abs = abs(x - tx)                  # 目标在 x 轴上的绝对坐标差
    dy_abs = abs(y - ty)                  # 目标在 y 轴上的绝对坐标差

    # 各轴上"朝目标"的那个方向；若该轴差为 0 则该轴没有方向，记为 None
    if tx > x:                   # 目标在右边
        x_dir = Facing.RIGHT
    elif tx < x:                 # 目标在左边
        x_dir = Facing.LEFT
    else:                        # 已在同一列，x 轴没有可走方向
        x_dir = None

    if ty > y:                   # 目标在上边
        y_dir = Facing.UP
    elif ty < y:                 # 目标在下边
        y_dir = Facing.DOWN
    else:                        # 已在同一行，y 轴没有可走方向
        y_dir = None

    # 谁的绝对坐标差大就先走谁的轴；相等时（本题取"保守自洽"的约定）先走 x 轴
    if dx_abs >= dy_abs:
        preferred, fallback = x_dir, y_dir
    else:
        preferred, fallback = y_dir, x_dir

    # 优先轴方向若是候选就走它；否则退回另一轴；再不行取枚举到的第一个
    if preferred in candidates:
        return preferred
    if fallback in candidates:
        return fallback
    return candidates[0]


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
    """纯函数决策：读感知/状态/血量/热量，返回 (action, new_state)。

    求值方式：严格按 R1→R7 顺序逐条判断，**首条命中立刻返回，永不例外**。
    因此规则之间天然互斥、覆盖完备，任一合法输入恰好命中一条。

    参数
    ----
    sensor : dict  形如
        {"enemy_frames": (True, False, True),  # 敌检历史，末位=当前帧，长 1-6
         "enemy_dist":   3,                     # 敌距，int 或 None
         "robot_type":   "INFANTRY",            # "INFANTRY" 或 "HERO"
         "max_hp":       120}
    state  : SentryState  当前状态机状态
    hp     : int          当前血量（与 max_hp 一起换算成 hp_pct）
    heat   : 当前热量；R1-R7 的规则表暂不使用，仅为接口预留

    raise ValueError 的三种"契约外"输入：
      1) enemy_frames 是空序列，或长度 > 6；
      2) state 不是 SentryState 的五个成员之一；
      3) sensor 缺少四个字段中的任意一个。
    注意：字段**存在但取值非法**（如 enemy_dist="far"）不算契约外，
    要按防御式方式归一化，不抛异常。
    """
    # sensor形式及其内容是否合法
    if not isinstance(sensor, dict):
        raise ValueError("sensor 必须是 dict")
    for key in ("enemy_frames", "enemy_dist", "robot_type", "max_hp"):
        if key not in sensor:                      # 第 3 种：缺字段
            raise ValueError("sensor 缺少必需字段: " + key)

    # 检验状态是否合法
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")

    # 检验enemy_frames的value是否合法
    frames_raw = sensor["enemy_frames"]
    if not isinstance(frames_raw, (tuple, list)):
        raise ValueError("enemy_frames 是 tuple 或 list")
    if len(frames_raw) == 0 or len(frames_raw) > 6:
        raise ValueError("enemy_frames 长度必须在 1-6")

    # 规范frame的布尔值
    frames = tuple(bool(f) for f in frames_raw)

    visible = frames[-1]

    # 规范enemy_dist的整数
    dist_raw = sensor["enemy_dist"]
    if dist_raw is None or isinstance(dist_raw, bool):
        # bool 是 int 的子类，但语义上不是"距离"，一并归一为 None
        enemy_dist = None
    elif isinstance(dist_raw, int):
        enemy_dist = dist_raw
    elif isinstance(dist_raw, float):
        enemy_dist = int(dist_raw)
    else:
        try:
            enemy_dist = int(str(dist_raw).strip())
        except (TypeError, ValueError):
            enemy_dist = None

    # 规范robot_type的类型
    type_raw = sensor["robot_type"]
    is_hero = isinstance(type_raw, str) and type_raw.strip().upper() == "HERO"

    # 规范整数的函数
    def to_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    max_hp_i = to_int(sensor["max_hp"], 100)   # 满血非法 → 默认 100
    hp_i = to_int(hp, 0)                       # 血量非法 → 默认 0

    if max_hp_i > 0:
        # 复用 Q1 的 hp_ratio
        hp_pct = hp_ratio(hp_i, max_hp_i)
    else:
        # 满血非法（会除零）：有血视为满血，无血视为 0
        hp_pct = 100 if hp_i > 0 else 0

    # 交火分支的公共判定：敌距 <= 3 为"贴身"，直接开火；
    # 敌距为 None（未知）时不算贴身
    close_range = (enemy_dist is not None and enemy_dist <= 3)

    # 交火分支的公共函数
    def engage_action():
        if close_range:
            return "SHOOT"                       # 敌距 <= 3：开火
        return "MOVE_RIGHT" if is_hero else "MOVE_LEFT"

    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)

   # 判断状态，并作出对应行动
    if state == SentryState.RETREAT:
        if hp_pct > 30:
            return ("RETURN", SentryState.RETURN)
        return ("RETREAT", SentryState.RETREAT)

    if state == SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)

    if state == SentryState.ENGAGE:
        # R4 看得见 → 按距离/机型出手，保持 ENGAGE
        if visible:
            return (engage_action(), SentryState.ENGAGE)
        if len(frames) >= 2 and not frames[-2]:
            return ("SCAN", SentryState.SUSPECT)
        return ("HOLD_FIRE", SentryState.ENGAGE)

    if visible:
        if len(frames) >= 2 and frames[-2]:
            return (engage_action(), SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)

    if state == SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)
    return ("SCAN", SentryState.SUSPECT)


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """Q6：把 Q3 的载体物理 + Q4 的贪心导航，组装成完整任务循环。

    每轮：sense（读载体状态）→ decide（选方向 / 是否脱困）→ act（先对齐朝向，
    再 move_forward）。终止条件：抵达 grid.enemy_pos / 步数用尽 / 电量耗尽。

    返回契约（键与类型固定，题面 Q6 规范 5）：
        {"steps": int, "collisions": int, "visited_count": int,
         "found_enemy": bool, "success": bool}

    策略总览（题面 Q6 规范 1）：
        - 平时用 Q4 的 next_step_toward 贪心选方向；
        - 当贪心"失速"（没有任何方向能让曼哈顿距离严格变小）时，切入
          【沿墙走】脱困模式：贴着某一侧的墙一直挪，绕出死角；
        - 当距离重新可缩短时，切回贪心。

    下面已给出完整骨架 + 可直接用的工具函数；
    【挖空 ①~④】是本功能的核心决策点，留给你写（记得删掉 raise 那行）。
    """
    target = grid.enemy_pos

    # ==================== 工具函数（已写好，直接用） ====================
    def manhattan(a, b):
        """两格间的曼哈顿距离（Q4 用的度量）。"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def has_greedy_candidate(pos):
        """当前格是否还存在"能让距离严格变小"的可走方向。

        与 Q4 的差别：这里把【越界】也算走不通（用 grid.is_blocked，
        它同时判断障碍与越界），所以它同时回答"贪心还能不能推进"。
        """
        cur = manhattan(pos, target)
        for f in Facing:
            d = f.delta
            nxt = (pos[0] + d[0], pos[1] + d[1])
            if not grid.is_blocked(*nxt) and manhattan(nxt, target) < cur:
                return True
        return False

    def rotate_to(f):
        """把朝向旋转到 f（能一步左转就左转，否则一路右转）。

        纯转向：不移动、不耗电。act 阶段先对齐朝向，再 move_forward。
        """
        rights = {Facing.UP: 0, Facing.RIGHT: 1,
                  Facing.DOWN: 2, Facing.LEFT: 3}
        diff = (rights[f] - rights[grid.facing]) % 4
        if diff == 3:          # 左转 1 次比右转 3 次更省动作
            grid.turn_left()
        else:
            for _ in range(diff):
                grid.turn_right()

    # 沿墙走要用的"左 / 右手邻居"查找表：
    #   左转 = 逆时针 90°，右转 = 顺时针 90°。
    left_of = {Facing.UP: Facing.LEFT, Facing.LEFT: Facing.DOWN,
               Facing.DOWN: Facing.RIGHT, Facing.RIGHT: Facing.UP}
    right_of = {v: k for k, v in left_of.items()}

    # ==================== 状态变量 ====================
    steps = 0                      # 已执行的动作数（= move_forward 的次数）
    visited = {grid.current_pos}   # 走过的格子（去重后用于 visited_count）
    wall = False                   # 是否处于"沿墙脱困"模式
    hand = "L"                     # 贴哪只手走："L"=左手贴墙，"R"=右手贴墙
    wall_steps = 0                 # 本次脱困已走的步数（绕圈超时用）
    entry_dist = 0                 # 进入脱困时到目标的距离（切回贪心用）

    # ==================== 主循环 ====================
    while steps < max_steps and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos  # sense：读载体状态

        # ---- decide 第 1 步：要不要【进入】沿墙脱困？ ----
        # 贪心失速 = 当前格没有任何方向能让曼哈顿距离严格变小。
        if (not wall) and (not has_greedy_candidate(pos)):
            # ✍️ 挖空 ①：初始化脱困模式（约 4 行）
            #    wall           → True（进入脱困）
            #    hand           → "L"（先试左手贴墙）
            #    wall_steps     → 0（本次脱困重新计时）
            #    entry_dist     → manhattan(pos, target)（记下入口距离，
            #                      用来判断之后是否"绕出来了、比入口更近"）
            wall = True
            hand = "L"
            wall_steps = 0
            entry_dist = manhattan(pos, target)

        # ---- decide 第 2 步：本步朝哪走？ ----
        if wall:
            # 沿墙走：贴着 hand 那一侧的墙挪。
            #   side     = 贴墙那一侧的相邻朝向
            #   opposite = side 的反方向（判断掉头用）
            side = left_of[grid.facing] if hand == "L" else right_of[grid.facing]
            opposite = (right_of[grid.facing] if hand == "L"
                        else left_of[grid.facing])

            def cell(f):
                """朝向 f 的相邻格坐标。"""
                d = f.delta
                return (pos[0] + d[0], pos[1] + d[1])

            # ✍️ 挖空 ②：沿墙的转向决策（本题最大的坑——转向顺序写反就废）
            #    按顺序判断三种情形：
            #      (a) 侧边没堵 → 朝侧边转（左手贴墙用 turn_left，
            #                       右手贴墙用 turn_right），然后贴墙挪；
            #      (b) 否则若【正前方】被堵 →
            #            若 opposite 侧没堵 → 朝它拐（turn_right / turn_left）；
            #            连 opposite 也堵（钻进死角）→ 原地掉头 180°（右转两次）；
            #      (c) 否则（前方没堵）→ 什么都不做，保持朝向前进。
            #    提示：turn_left()/turn_right() 只改朝向并返回新朝向。
            if not grid.is_blocked(*cell(side)):
                # (a) 侧边空 → 朝侧边转，然后贴墙挪
                if hand == "L":
                    grid.turn_left()
                else:
                    grid.turn_right()
            elif grid.is_blocked(*cell(grid.facing)):
                # (b) 前方堵 → 能拐就拐，拐不了（死角）就掉头
                if not grid.is_blocked(*cell(opposite)):
                    if hand == "L":
                        grid.turn_right()
                    else:
                        grid.turn_left()
                else:
                    grid.turn_right()      # 原地转 180°
                    grid.turn_right()
            # (c) 否则前方没堵 → 什么都不做，保持朝向前进
        else:
            # 贪心：Q4 给一个方向，再把朝向对齐过去。
            direction = next_step_toward(pos, target, grid.obstacles,
                                         grid.facing)
            rotate_to(direction)

        # ---- act：对齐朝向之后，前进一格 ----
        grid.move_forward()
        steps += 1
        visited.add(grid.current_pos)

        # ---- 脱困模式的维护 ----
        if wall:
            wall_steps += 1
            limit = grid.width + grid.height   # 绕圈超时阈值（题面允许自定）

            # ✍️ 挖空 ③：绕圈太久 → 换手 / 放弃脱困
            #    贴一只手走太久还出不去，多半是这只手贴错了墙：
            #      - 若 hand == "L" 且 wall_steps > limit：
            #            换成 "R"，并把 wall_steps 归零；
            #      - 否则若 wall_steps > 2 * limit：
            #            放弃脱困，wall = False（切回贪心再试）。
            #
            # ✍️ 挖空 ④：绕出来了 → 切回贪心
            #    判据：当前位置既能贪心推进、又比【入口距离】更近了：
            #      elif has_greedy_candidate(grid.current_pos) and \
            #           manhattan(grid.current_pos, target) < entry_dist + 1:
            #          wall = False
            if wall_steps > limit and hand == "L":
                hand = "R"               # 左手贴错了墙 → 换右手
                wall_steps = 0
            elif wall_steps > 2 * limit:
                wall = False             # 绕太久，放弃脱困，切回贪心
            elif (has_greedy_candidate(grid.current_pos)
                  and manhattan(grid.current_pos, target) < entry_dist + 1):
                wall = False             # 贪心重新可推进且比入口更近 → 绕出来了

    # ==================== 收尾：按契约返回统计 ====================
    # visited_count 的"去过多少格"题面未钉死，这里取【去重后的格子数】：
    # 含起点、同格多次只算一次。保持确定性即可。
    return {
        "steps": steps,
        "collisions": grid.collision_count,
        "visited_count": len(visited),
        "found_enemy": grid.found_enemy,
        "success": grid.found_enemy,        # 与 found_enemy 同义
    }


def report_to_json(stats):
    """把统计字典序列化为【确定性】的 JSON 字符串（题面 Q6 规范 6）。

    确定性 = 同样的 stats 永远得到字节级相同的字符串。
    为此序列化参数必须固定：键顺序、分隔符、非 ASCII 处理、数值格式。

    ✍️ 挖空 ⑤：给 json.dumps 选出"确定性"的参数。
       提示：
         - sort_keys=True         → 键按字典序输出，不依赖 dict 插入顺序
         - separators=(",", ":")  → 去掉默认多余空格，输出紧凑且固定
         - ensure_ascii 选 True/False 都行，但要固定（本题键值全 ASCII）
    验收方式：自动测试多半是"两次调用结果相等 + 能 json.loads 还原"，
    所以只要参数固定、别混入 NaN/Infinity 之类的非标准值即可。
    """
    return json.dumps(stats, sort_keys=True, separators=(",", ":"))


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
