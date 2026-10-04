"""活动加成时段：按时段表查询某一时刻生效的加成。

口径（README 为准）：
- 半开区间 [start_ms, end_ms)，等于结束时刻算已结束。
- end_ms 不大于 start_ms 的时段拒绝登记，返回 False，不写入台账。
- 同一 kind 只保留优先级最高的一条，同优先级按 activity_id 升序取第一条；
  不同 kind 各自保留，结果按 kind 升序。
- 同一 activity_id 重复登记返回 False，不覆盖已有记录。
- 查询走中点区间树，只检查真正覆盖该时刻的时段，单次摊还 O(命中数)；
  相邻事件边界之间的结果再按段缓存，重复查询零扫描。
"""

from bisect import bisect_left, bisect_right


class _Node:
    __slots__ = ("center", "left", "right", "by_start", "by_end", "starts", "ends")

    def __init__(self, center, left, right, by_start, by_end):
        self.center = center
        self.left = left
        self.right = right
        self.by_start = by_start          # 覆盖 center 的时段，按 start 升序
        self.by_end = by_end              # 同一批时段，按 end 升序
        self.starts = [rec[0] for rec in by_start]
        self.ends = [rec[1] for rec in by_end]


def _build(records):
    """records: [(start, end, kind, rate, priority, activity_id), ...]，按 start 升序。"""
    if not records:
        return None
    center = records[len(records) // 2][0]
    left, mid, right = [], [], []
    for rec in records:
        if rec[1] <= center:
            left.append(rec)
        elif rec[0] > center:
            right.append(rec)
        else:
            mid.append(rec)
    by_end = sorted(mid, key=lambda rec: rec[1])
    return _Node(center, _build(left), _build(right), mid, by_end)


class Boosts:
    """活动时段台账。"""

    def __init__(self):
        self.windows = {}
        self.scanned = 0
        self._root = None
        self._bounds = []
        self._cache = {}
        self._dirty = False

    def add(self, activity_id, start_ms, end_ms, kind, rate, priority=0):
        """登记一个活动时段。非法区间或重复 activity_id 返回 False。"""
        if end_ms <= start_ms:
            return False
        if activity_id in self.windows:
            return False
        self.windows[activity_id] = (start_ms, end_ms, kind, rate, priority)
        self._dirty = True
        return True

    def _rebuild(self):
        records = sorted(
            (start, end, kind, rate, priority, activity_id)
            for activity_id, (start, end, kind, rate, priority) in self.windows.items()
        )
        self._root = _build(records)
        bounds = set()
        for rec in records:
            bounds.add(rec[0])
            bounds.add(rec[1])
        self._bounds = sorted(bounds)
        self._cache = {}
        self._dirty = False

    def _compute(self, now_ms):
        """沿区间树收集覆盖 now_ms 的时段，按口径取每 kind 最优。"""
        best = {}
        node = self._root
        while node is not None:
            if now_ms < node.center:
                limit = bisect_right(node.starts, now_ms)
                self.scanned += limit
                for rec in node.by_start[:limit]:
                    key = (-rec[4], rec[5])
                    kind = rec[2]
                    if kind not in best or key < best[kind][0]:
                        best[kind] = (key, rec[3])
                node = node.left
            else:
                limit = bisect_right(node.ends, now_ms)
                self.scanned += len(node.by_end) - limit
                for rec in node.by_end[limit:]:
                    key = (-rec[4], rec[5])
                    kind = rec[2]
                    if kind not in best or key < best[kind][0]:
                        best[kind] = (key, rec[3])
                node = node.right
        return [(kind, best[kind][1]) for kind in sorted(best)]

    def active_at(self, now_ms):
        """返回该时刻生效的加成列表 [(kind, rate), ...]，按 kind 升序。"""
        if self._dirty:
            self._rebuild()
        index = bisect_right(self._bounds, now_ms) - 1
        if index < 0:
            return []
        if index not in self._cache:
            self._cache[index] = self._compute(self._bounds[index])
        return list(self._cache[index])

    def scanned_count(self):
        return self.scanned
