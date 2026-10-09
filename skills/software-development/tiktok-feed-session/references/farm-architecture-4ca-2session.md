# Kiến trúc Farm: 4 Ca × 2 Phiên (Cập nhật 09/09/2026)

## Tổng quan

- **80 máy**, mỗi máy **8 acc (Row 1–8)**.
- **4 ca/ngày** rải đều 6 tiếng: `06:00` → `12:00` → `18:00` → `00:00`.
- **2 phiên/ca**: Phiên 1 = lướt feed (30-35p), phiên 2 = lướt feed + follow hook + video hook.
- **Gap giữa phiên**: 40–60 phút (pair_gap ngẫu nhiên).

## Lane theo ngày

- **Ngày lẻ**: Lane B → Row 1, 3, 5, 7
- **Ngày chẵn**: Lane A → Row 2, 4, 6, 8

## Scheduler (hermes_cron/blocks.py)

```python
BLOCK_ANCHORS = ("06:00", "12:00", "18:00", "00:00")
LANES = (("A", (2, 4, 6, 8)), ("B", (1, 3, 5, 7)))
```

- `_anchor_for`: block_index in `(1, 2, 3, 4)`
- `build_block_sessions`: trả tuple 2 phiên `(s1, s2)`:
  - s1_start = anchor + jitter (±25 phút, grid 5 phút)
  - s1_end = s1_start + 60 phút
  - s2_start = s1_end + pair_gap (35-60 phút)
  - s2_end = s2_start + 60 phút
- `AccountBlock.session_slots`: `tuple[tuple[str, str], tuple[str, str]]`

## Picker (hermes_cron/picker.py)

- Loop: `for block_index in (1, 2, 3, 4)`
- Map row theo block_index trong lane_today

## Manifest (hermes_cron/manifest.py)

```python
CONSTRAINTS = {
    "blocks_per_machine_day": 4,
    "sessions_per_block": 2,
    "feed_row_max": 8,
    "block_anchors": ["06:00", "12:00", "18:00", "00:00"],
}
```

- Validator kiểm tra block_index in `(1..4)`, entry_ids len == 2, session_index in `(1, 2)`

## Watchdog (feed_session_watchdog.py)

```python
SESSION_WINDOWS = [
    # Ca 1 (Sáng)
    {"ca": 1, "phien": 1, "name": "Ca 1 - Phiên 1/2", "start": "06:00", "end": "07:30"},
    {"ca": 1, "phien": 2, "name": "Ca 1 - Phiên 2/2", "start": "07:30", "end": "10:00"},
    # Ca 2 (Trưa)
    {"ca": 2, "phien": 1, "name": "Ca 2 - Phiên 1/2", "start": "12:00", "end": "13:30"},
    {"ca": 2, "phien": 2, "name": "Ca 2 - Phiên 2/2", "start": "13:30", "end": "16:00"},
    # Ca 3 (Tối)
    {"ca": 3, "phien": 1, "name": "Ca 3 - Phiên 1/2", "start": "18:00", "end": "19:30"},
    {"ca": 3, "phien": 2, "name": "Ca 3 - Phiên 2/2", "start": "19:30", "end": "22:00"},
    # Ca 4 (Đêm)
    {"ca": 4, "phien": 1, "name": "Ca 4 - Phiên 1/2", "start": "00:00", "end": "01:15"},
    {"ca": 4, "phien": 2, "name": "Ca 4 - Phiên 2/2", "start": "01:15", "end": "03:00"},
]
```

- Cửa sổ half-open `[start, end)` ngoại trừ window cuối ngày `[start, end]`.
- Mỗi máy có 40-60 phút nghỉ giữa 2 phiên (pair_gap).

## Follow Budget (follow_runner/core/config.py)

- `budget_per_day: 35` (tổng/ngày/acc)
- `budget_per_session: 18` (mỗi phiên ~17-18 follow)
- `budget_per_session_min: 15`
- `budget_per_session_max: 18`
- Video gate: `>=5` video mới được follow
- Tick rate: ~2 phút/follow → hành vi tự nhiên

## Timeline 1 ngày (1 máy)

| Ca | Phiên | Khung giờ | Hoạt động | Nghỉ |
|---|---|---|---|---|
| 1 | 1 | 06:00-07:30 | Feed lướt | — |
| 1 | 2 | 07:30-10:00 | Feed + Follow + Video hook | 10:00-12:00 (nghỉ 2h) |
| 2 | 1 | 12:00-13:30 | Feed lướt | — |
| 2 | 2 | 13:30-16:00 | Feed + Follow + Video hook | 16:00-18:00 (nghỉ 2h) |
| 3 | 1 | 18:00-19:30 | Feed lướt | — |
| 3 | 2 | 19:30-22:00 | Feed + Follow + Video hook | 22:00-00:00 (nghỉ 2h) |
| 4 | 1 | 00:00-01:15 | Feed lướt | — |
| 4 | 2 | 01:15-03:00 | Feed + Follow + Video hook | 03:00-06:00 (nghỉ 3h) |
