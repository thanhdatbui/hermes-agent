# Scheduler Migration: 3 Ca × 3 Phiên → 4 Ca × 2 Phiên (09/09/2026)

## Mục tiêu
Chuyển hệ thống nuôi TikTok từ 3 ca × 3 phiên (6 acc/máy: Row 1-6) sang **4 ca × 2 phiên (8 acc/máy: Row 1-8)**.

## Cấu hình chốt
- **BLOCK_ANCHORS**: `("06:00", "12:00", "18:00", "00:00")`
- **LANES**: `(("A", (2, 4, 6, 8)), ("B", (1, 3, 5, 7)))`
- Ngày Lẻ (Lane B): Block 1=Row1, Block 2=Row3, Block 3=Row5, Block 4=Row7
- Ngày Chẵn (Lane A): Block 1=Row2, Block 2=Row4, Block 3=Row6, Block 4=Row8
- **Phiên 2 là phiên cuối ca** → kích hoạt upload hook (đăng video) + follow hook
- Nghỉ giữa 2 phiên: `pair_gap` ngẫu nhiên 35-60 phút tự nhiên theo từng máy (không phải liền nhau)
- **Follow budget**: `budget_per_session: 18` (range 15-18), `budget_per_day: 35` (giữ nguyên)

## Các file đã thay đổi
| File | Thay đổi |
|------|----------|
| `python_runner/hermes_cron/blocks.py` | BLOCK_ANCHORS 4 ca, LANES Row 1-8, build_block_sessions 2 sessions |
| `python_runner/hermes_cron/picker.py` | loop block_index 1-4, successes_today cap 2 |
| `python_runner/hermes_cron/manifest.py` | CONSTRAINTS feed_row_max=8, blocks_per_machine_day=4, sessions_per_block=2; validator 2 sessions, account 1 block/day |
| `python_runner/flows/multi_machine_feed_session.py` | Upload hook gate session_index 2 (từ 3), clear_cache gate block_index 4 |
| `python_runner/tests/test_hermes_cron_contract.py` | Golden vector hashes recomputed |
| `python_runner/tests/test_upload_hook_alerts.py` | `_session_index` fixture 2 |
| `scripts/hermes_cron/feed_session_watchdog.py` | SESSION_WINDOWS 4 ca × 2 phiên |
| `D:\Taadaa\tiktok-follow\follow_runner\config.example.yaml` | budget_per_session min 15 max 18 |
| `D:\Taadaa\tiktok-follow\config\machine*.yaml` | budget_per_session min 15 max 18 (17 files) |

## Watchdog SESSION_WINDOWS mới
```python
SESSION_WINDOWS = [
    {"ca": 1, "phien": 1, "name": "Ca 1 - Phiên 1/2 (Sáng)", "start": "06:00", "end": "07:30"},
    {"ca": 1, "phien": 2, "name": "Ca 1 - Phiên 2/2 (Sáng - Đăng video)", "start": "07:30", "end": "10:00"},
    {"ca": 2, "phien": 1, "name": "Ca 2 - Phiên 1/2 (Chiều)", "start": "12:00", "end": "13:30"},
    {"ca": 2, "phien": 2, "name": "Ca 2 - Phiên 2/2 (Chiều - Đăng video)", "start": "13:30", "end": "16:00"},
    {"ca": 3, "phien": 1, "name": "Ca 3 - Phiên 1/2 (Tối)", "start": "18:00", "end": "19:30"},
    {"ca": 3, "phien": 2, "name": "Ca 3 - Phiên 2/2 (Tối - Đăng video)", "start": "19:30", "end": "22:00"},
    {"ca": 4, "phien": 1, "name": "Ca 4 - Phiên 1/2 (Đêm)", "start": "00:00", "end": "01:15"},
    {"ca": 4, "phien": 2, "name": "Ca 4 - Phiên 2/2 (Đêm - Đăng video)", "start": "01:15", "end": "03:00"},
]
```

## Golden Vector Hash Update (CONSTRAINTS thay đổi kéo theo)
Khi CONSTRAINTS thay đổi, file `python_runner/tests/test_hermes_cron_contract.py` có 2 assert cần tính lại:
```python
# Tính assignment hash mới:
python -c "
import hashlib, json, sys
sys.path.insert(0, 'D:/Taadaa/tiktok-luot nuoi acc')
PYTHONPATH='D:/Taadaa/tiktok-luot nuoi acc' # cần set trước
from python_runner.hermes_cron.manifest import CONSTRAINTS
from python_runner.tests.test_hermes_cron_contract import stdlib_reference_bytes
# ... (paste normalized + src_rev computation from test)
inp = {'account_ids': ['acct-a'], 'constraints': CONSTRAINTS, ...}
print('assignment:', 'assignment-v1-' + hashlib.sha256(stdlib_reference_bytes(inp)).hexdigest()[:32])
"
# Sau khi có assignment hash mới, tính entry hash theo cùng pattern
```
Patch dòng assert bằng hash mới, chạy pytest kiểm tra.

## Delegation Micro-Task Anti-Timeout Pattern
**Vấn đề**: Worker subagent bị timeout 600s khi nhận scope lớn (5 file + chạy pytest).

**Giải pháp**: Chia thành micro-task 1-2 file, cung cấp sẵn Python script thực thi trong phần context:
```
File 1-2: blocks.py + picker.py → 2 phút
File 3: manifest.py (dùng script string-replace sẵn) → 2 phút
File 4: multi_machine_feed_session.py (4 điểm replace sẵn) → 20 giây
File 5: feed_session_watchdog.py → 2 phút
File 6: fix test fixtures → 7 phút (bao gồm pytest verify)
```

**Khi đưa script Python thực thi trực tiếp trong context** (không để worker tự nghĩ cách replace), worker hoàn thành trong 1-2 tool calls thay vì tốn 10 tool calls tìm hiểu cấu trúc.

## Follow Budget Formula khi thay đổi số phiên
```
budget_per_session = ceil(budget_per_day / sessions_per_day_per_acc)
# Với 2 phiên/acc/ngày và budget_per_day=35: ceil(35/2) = 18
# Random range: min = floor(35/2) - 3 = 15, max = 18
# Giữ budget_per_day cố định, chỉ nâng budget_per_session
```

## Notes
- Hàm `_is_final_block3_session` vẫn giữ tên cũ (legacy), nội dung đã sửa check block_index==4 & session_index==2. Rename sang `_is_final_block4_session` trong session sau.
- Ca 4 anchor 00:00 dùng logical day hiện tại (không +1 ngày) vì scheduler đã có window_start/end mechanism.
- Git commit tiktok-luot nuoi acc: `4891fec` / tiktok-follow: `0c94342`
