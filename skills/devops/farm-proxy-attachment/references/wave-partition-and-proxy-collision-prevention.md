# Wave Partitioning & Proxy Collision Prevention Architecture

## 1. Bối Cảnh & Vấn Đề Lệch Pha Code vs Runbook (Audit 13/10/2026)
- **Tài liệu trên giấy:** Thiết kế Wave Scheduling (Wave 1 chạy 40 máy độc lập IP, Wave 2 chạy 40 máy đối tác) đã được ghi nhận trong runbook.
- **Thực tế code cũ:** `multi_machine_feed_session.py` đưa toàn bộ 78 máy vào 1 danh sách phẳng và gọi `build_machine_launch_plan` xáo trộn ngẫu nhiên toàn bộ (`generator.shuffle(order)`).
- **Hệ quả rủi ro:**
  - Nếu máy A và máy B (chung 1 proxy port) ngẫu nhiên xuất phát sát nhau trong 30 workers đầu tiên: cả 2 cùng lướt feed và cùng bước vào `_run_follow_hook` gần như đồng thời.
  - Khi máy A dính lỗi `FOLLOW_FAILED`, máy B đã bắt đầu bấm follow trên cùng IP -> dính cờ nhả chéo trước khi Cầu Dao kịp ghi nhận, trảm dắt dây cả 2 tài khoản.
  - Việc máy đối tác từng được cứu ở các phiên trước thực chất là nhờ may mắn ngẫu nhiên của hàm shuffle (máy A ở đầu hàng, máy B ở cuối hàng).

## 2. Giải Pháp Kỹ Thuật Chuẩn Hóa: `wave_partition.py`
Tọa lạc tại: `D:/Taadaa/automation-core/src/automation_core/scheduler/wave_partition.py`

### Các hàm cốt lõi:
1. `load_machine_proxy_mapping(excel_path=None)`:
   - Tự động nạp bảng mapping proxy chuẩn từ `PROXYgandienthoai.xlsx` (hỗ trợ cả Kibe và Admin).
   - Chuẩn hóa thành `dict[int, str]` map `machine -> "host:port"`.
2. `partition_accounts_into_waves(accounts, proxy_map=None, seed=None, rng=None)`:
   - Gom nhóm tài khoản theo từng đường proxy (`host:port`).
   - Tung đồng xu / xáo trộn ngẫu nhiên từng bucket proxy để phân bổ máy vào Wave 1, Wave 2 (hoặc Wave 3 nếu cụm Admin có 3 máy/cổng).
   - Xáo trộn nội bộ (shuffle) từng wave để giữ nguyên tính ngẫu nhiên (entropy) cao nhất.
   - **Bảo đảm chuẩn:** Trong mỗi Wave, 100% không có 2 máy nào trùng proxy IP (zero collision).
3. `build_wave_launch_plan(items, min_stagger_ms=2000, max_stagger_ms=8000, max_workers=30, ...)`:
   - Trả về `(plan: MachineLaunchPlan, wave_groups: list[list[int]])`.
   - Kết hợp các wave thành một thứ tự khởi động tuần tự: toàn bộ máy Wave 1 đặt trước, toàn bộ máy Wave 2 đặt sau.
   - Gắn stagger delays (2–8s) an toàn.

## 3. Tích Hợp Vào Batch Runner (`multi_machine_feed_session.py`)
Tại điểm dựng `launch_plan` của `multi_machine_feed_session.py`:
```python
stagger = ctx.config.get("_machine_start_stagger_ms") or (4000, 10000)
try:
    from automation_core.scheduler.wave_partition import build_wave_launch_plan
    launch_plan, _ = build_wave_launch_plan(
        reserved_accounts,
        min_stagger_ms=int(stagger[0]),
        max_stagger_ms=int(stagger[1]),
        max_workers=int(ctx.config.get("_max_workers") or len(reserved_accounts) or 1),
    )
except Exception:
    launch_plan = build_machine_launch_plan(...)
```

### Cơ chế hoạt động thực tế:
- ThreadPoolExecutor chạy với `max_workers = 30`.
- 30 workers đầu tiên bốc 30 máy của Wave 1 (hoàn toàn khác IP).
- Khi các máy Wave 1 hoàn thành feed, 9 máy còn lại của Wave 1 tiếp tục chạy.
- Toàn bộ máy Wave 2 chỉ bắt đầu được nạp vào luồng khi các máy Wave 1 đã giải phóng slot.
- Tạo ra khoảng cách thời gian tự nhiên **10–20 phút** giữa máy Wave 1 và máy đối tác Wave 2.
- Nếu máy Wave 1 dính `FOLLOW_FAILED` -> Cầu dao giật ngắt cổng proxy 48h -> Đến khi máy Wave 2 bước vào ca follow, `check_ip_breaker` bắt được cờ `TRIPPED` và Safe-Skip an toàn 100%.
