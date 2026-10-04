"""活动加成时段：按时段表查询某一时刻生效的加成。

口径（以 README 为准）：

- 时段是半开区间 ``[start_ms, end_ms)``，正好等于结束时刻算已结束。
- ``end_ms <= start_ms`` 的时段非法，拒绝登记且不写入台账。
- 同一 ``kind`` 同时命中多条时只保留优先级最高的一条，同优先级按
  ``activity_id`` 升序；不同 kind 各自保留，结果按 kind 升序。
- 同一 ``activity_id`` 重复登记返回 False 且不覆盖已有记录。
- 查询走分 kind 的获胜者时间线（登记后惰性重建），单次查询按
  ``bisect`` 定位，不再全扫历史时段；同一时刻的重复查询直接走缓存。
"""

import bisect
import heapq
from collections import defaultdict


class Boosts:
    """活动时段台账。"""

    _CACHE_LIMIT = 4096

    def __init__(self):
        self.windows = {}
        self._kinds = []
        self._by_kind = defaultdict(list)
        self._timelines = {}
        self._dirty = False
        self._cache = {}
        self.scanned = 0

    def add(self, activity_id, start_ms, end_ms, kind, rate, priority=0):
        """登记一个活动时段。

        非法时段（``end_ms <= start_ms``）或重复 ``activity_id`` 返回
        False，且不写入台账、不覆盖已有记录。
        """
        if end_ms <= start_ms:
            return False
        if activity_id in self.windows:
            return False
        record = (start_ms, end_ms, kind, rate, priority)
        self.windows[activity_id] = record
        if kind not in self._by_kind:
            bisect.insort(self._kinds, kind)
        self._by_kind[kind].append((activity_id,) + record)
        self._dirty = True
        self._cache.clear()
        return True

    def active_at(self, now_ms):
        """返回该时刻生效的加成，形如 ``[(kind, rate), ...]``，按 kind 升序。"""
        cached = self._cache.get(now_ms)
        if cached is not None:
            return list(cached)
        if self._dirty:
            self._rebuild()
        out = []
        for kind in self._kinds:
            self.scanned += 1
            starts, ends, rates = self._timelines[kind]
            index = bisect.bisect_right(starts, now_ms) - 1
            if index >= 0 and now_ms < ends[index]:
                out.append((kind, rates[index]))
        if len(self._cache) >= self._CACHE_LIMIT:
            self._cache.clear()
        self._cache[now_ms] = out
        return list(out)

    def scanned_count(self):
        return self.scanned

    def _rebuild(self):
        self._timelines = {}
        for kind, records in self._by_kind.items():
            self._timelines[kind] = _winner_timeline(records)
        self._dirty = False


def _winner_timeline(records):
    """把同一 kind 的时段折叠为获胜者（rate）时间线。

    扫描所有起止点，用按 ``(-priority, activity_id)`` 排序的堆维护当前
    生效集合；相邻初等区间若获胜 rate 相同则合并。
    返回三条等长列表：区间起点、区间终点、获胜 rate（均为半开区间）。
    """
    points = sorted({rec[1] for rec in records} | {rec[2] for rec in records})
    by_start = defaultdict(list)
    for rec in records:
        by_start[rec[1]].append(rec)

    heap = []  # (-priority, activity_id, end_ms, rate)
    starts = []
    ends = []
    rates = []
    prev = None
    for point in points:
        if prev is not None and prev < point:
            while heap and heap[0][2] <= prev:
                heapq.heappop(heap)
            if heap:
                rate = heap[0][3]
                if starts and ends[-1] == prev and rates[-1] == rate:
                    ends[-1] = point
                else:
                    starts.append(prev)
                    ends.append(point)
                    rates.append(rate)
        for rec in by_start.get(point, ()):
            activity_id, start, end, kind, rate, priority = rec
            heapq.heappush(heap, (-priority, activity_id, end, rate))
        prev = point
    return starts, ends, rates
