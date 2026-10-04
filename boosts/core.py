"""活动加成时段：按时段表查询某一时刻生效的加成。

缺陷：时段按闭区间处理、同类不取最高优先级、activity_id 重复登记直接覆盖、
非法时段照收、每次查询全扫历史时段。
"""


class Boosts:
    """活动时段台账。"""

    def __init__(self):
        self.windows = {}
        self.scanned = 0

    def add(self, activity_id, start_ms, end_ms, kind, rate, priority=0):
        """登记一个活动时段。缺陷：不校验区间、重复登记直接覆盖。"""
        self.windows[activity_id] = (start_ms, end_ms, kind, rate, priority)
        return True

    def active_at(self, now_ms):
        """返回该时刻生效的加成。缺陷：闭区间、同类取第一条、全扫历史。"""
        self.scanned += len(self.windows)
        out = []
        kinds = set()
        for activity_id, (start, end, kind, rate, priority) in self.windows.items():
            if start <= now_ms <= end:
                if kind in kinds:
                    continue
                kinds.add(kind)
                out.append((kind, rate))
        return out

    def scanned_count(self):
        return self.scanned
