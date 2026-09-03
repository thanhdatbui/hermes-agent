# Scheduling overhaul pitfalls — đổi sessions/anchors/jitter trong hermes_cron

Bài học 2026-08-16 (plan "3 phiên/ca + jitter + follow hook"): khi đổi cấu trúc lịch chạy (sessions_per_block, anchors, pair_gap grid, jitter, inter-block gap) trong `python_runner/hermes_cron/`, có **coupling ẩn** phá crash nếu không sửa đồng bộ. Worker subagent phát hiện qua phân tích trước khi implement (hết budget ở giai đoạn đó, nhưng cứu khỏi commit vỡ).

## 1. manifest.py hardcode CONSTRAINTS — đổi blocks/picker KHÔNG đủ

`manifest.py` chứa `CONSTRAINTS` dict + validators **hardcode** giá trị cũ:
- `CONSTRAINTS`: `sessions_per_block: 2`, `pair_gap_minutes: [60,90]`, `inter_block_gap_minutes: [180,300]`, `slot_grid_minutes: 15`, `block_anchors: ["07:00","14:00","21:00"]`
- Validators hardcode: `pair_gap not in (60,75,90)` (line ~392), `session_index not in (1,2)` (~423), `len(block_entries) != 2 or session_index != [1,2]` (~447), `inter-block < 180` (~491), `session_slots != build_block_sessions(...)` (~397)
- `picker.py` gọi `validate_manifest` NGAY sau khi build → nếu manifest.py không theo kịp → **crash `SOURCE_CONFIG_INVALID` ngay lúc pick**, không phải lúc chạy.

→ **QUY TẮC:** đổi số sessions/anchors/gap = sửa ĐỒNG BỘ 3 nơi: `blocks.py` (constants + build), `manifest.py` (CONSTRAINTS + validators), `picker.py` (loop + emit). Không được chỉ đổi 1 nơi.

## 2. models.py SLOT_GRID_MINUTES ngoài allowlist

`SLOT_GRID_MINUTES = 15` nằm trong `models.py` (KHÔNG phải blocks.py) — đổi grid 15→5 phải sửa models.py nữa. `is_schedulable_interval` dùng nó để check slot align. Khi lập allowlist cho task scheduling, **luôn include models.py** nếu đụng grid.

## 3. Jitter âm phá window start — clamp block 1

Anchor block 1 = 06:00 = **window start** (`is_in_logical_window` từ 06:00). Jitter âm (-15/-20) → s1 = 05:45/05:40 **trước window** → `is_schedulable_interval` reject (`RESERVED_BLOCK_CONFLICT`). 

→ **Fix:** clamp jitter block 1 về ≥ 0; blocks 2/3 (anchor 12:30/19:00 sâu trong window) giữ ±20 đầy đủ.
```python
if block_index == 1 and jitter < 0:
    jitter = 0
```

## 4. Inter-block gap check dùng slot THỰC vs NOMINAL

Jitter làm gap thực giữa block < nominal (vd nominal 90', jittered 65-85'). Manifest validator check `< 90'` trên slot thực → reject dù design "anchor cố định quyết định". → **check trên nominal (unjittered) slots** — dùng `build_block_sessions(..., jitter_minutes=0)` cho feasibility, không dùng slot jittered.

## 5. Reactive phiên 2/3 cần 2 cơ chế MỚI (audit phát hiện)

Đổi từ "giờ cố định trong manifest" sang "phiên sau = xong phiên trước + random 35-60'":
- **PHẢI có ai đó GHI `last_feed_success_at`** sau phiên success (code cũ chỉ ĐỌC, không ai WRITE) — nếu không reactive không bao giờ kích hoạt.
- **PHẢI có cap sessions/ngày** (`sessions_today = count(success_timestamps hôm nay); ≥ 3 → NOT_DUE`) — `_feed_decision` chỉ check elapsed ≥ 2 ngày, không đếm phiên/ngày → reactive chạy 4-5 phiên/ngày nếu không chặn.
- Manifest chỉ phiên 1 có giờ cố định (anchor+jitter); phiên 2/3 đánh dấu reactive — runner bỏ qua slot_time cố định.

## 6. Golden vector / hash CONSTRAINTS trong tests

`test_hermes_cron_contract.py` golden vector chứa hash của CONSTRAINTS + `slot_time "07:00"` + `len(grid_slots)==77`. Đổi CONSTRAINTS → hash đổi → **phải recompute từ output thật** (chạy code lấy giá trị mới, KHÔNG tự đoán). Tương tự `test_hermes_cron_fleet.py` hardcode `len(entries)==6` → 9, `session_index ∈ [1,2]` → [1,2,3], `entry[5]` → `entry[8]`.

## 7. Subagent budget: 2 worker liên tiếp hết 100 api_calls ở phân tích

- Worker 1 (deleg): 100 api_calls hết khi chỉ đọc plan + khảo sát code — CHƯA sửa gì.
- Worker 2: 100 api_calls hết sau khi sửa xong RED tests — CHƯA implement GREEN.
- → **Quy tắc:** task scheduling overhaul (nhiều file coupling) quá lớn cho 1 subagent 100-call. Tách: (a) worker A chỉ phân tích + liệt kê coupling (như worker 1 — valuable!), (b) session tự implement code, (c) worker B chỉ sửa tests theo pattern. Hoặc session-as-worker ngay từ đầu cho phần GREEN (không bị giới hạn 100-call như subagent).
- Worker phát hiện coupling (manifest.py hardcode) TRƯỚC khi sửa = đúng giá trị — đừng coi "chưa làm gì" là fail; đó là discovery phase.

## 8. Subagent sửa tests "sai" nhưng phát hiện bug thật

Worker 3 (chỉ được sửa tests) phải sửa thêm 2 production files vì code tôi implement có bug thật:
- `picker.py`: thiếu clamp jitter block 1 (mục 3)
- `manifest.py`: validator thiếu `jitter_minutes` trong required_keys (picker emit 13 keys, validator đòi 12 → mọi block reject); `entry_ids` len check còn `!= 2`; `session_slots` canonical check bỏ qua jitter

→ **Dạy:** dù giao "chỉ sửa tests", worker có quyền sửa production nếu test không thể xanh vì bug thật — nhưng PHẢI báo rõ trong summary (worker 3 làm đúng). Session verify lại từng fix.
