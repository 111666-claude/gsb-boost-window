# boost-window

活动加成时段：按时段表查询某一时刻生效的加成，只用 Python 标准库。

```
python3 -m boosts.cli --sample boundary
python3 -m boosts.cli --sample priority
python3 -m boosts.cli --sample dup
python3 -m boosts.cli --sample scan
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **半开区间**：时段是 `[start_ms, end_ms)`；正好等于结束时刻算已经结束，不再生效。
- **合法性**：`end_ms` 不大于 `start_ms` 的时段拒绝登记并返回 False，不写入台账。
- **同类取最高优先级**：同一个 `kind` 同时命中多条时只保留优先级最高的一条，
  优先级相同按 `activity_id` 升序取第一条；不同 `kind` 各自保留，结果按 `kind` 升序。
- **幂等**：同一个 `activity_id` 重复登记返回 False，不覆盖已有记录。
- **查询代价**：`active_at` 不许每次全扫历史时段，`scanned_count()` 不随时段数乘查询次数增长。
- **规模**：50 万条时段、每秒 10 万次查询，单次摊还 O(命中数)。

## 输出契约（不改格式）

```
count=..
rate=..
second=.. rate=..
scanned=..
```

## 目录

```
boosts/core.py   时段区间、优先级覆盖与幂等登记
boosts/cli.py    命令行入口
tests/           unittest 用例
```
