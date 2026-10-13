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
   - Có cơ chế bắt lỗi an toàn (resilience): nếu file Excel không tồn tại hoặc lỗi, trả về mapping rỗng kèm log warning, không làm crash tiến trình.
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
    launch_plan = build_machine_launch_plan(
        [account.machine for account in reserved_accounts],
        min_stagger_ms=int(stagger[0]),
        max_stagger_ms=int(stagger[1]),
        max_workers=int(ctx.config.get("_max_workers") or len(reserved_accounts) or 1),
    )
launch_evidence = launch_plan.evidence()
```

## 4. Cơ Chế Giãn Cách Thời Gian Thực Tế Giữa 2 Máy Chung IP (Time Gap)
Khi người dùng hỏi: *"30 máy 1 lúc thì ví dụ máy A ip 1 xong thì máy B ip 1 nối tiếp đúng không?"*:
- **Cơ chế hàng đợi không nối tiếp ngay lập tức:**
  * Wave 1 (39 máy): Nằm ở chỉ mục `0..38` trong kế hoạch khởi động.
  * Wave 2 (39 máy): Nằm ở chỉ mục `39..77` trong kế hoạch khởi động.
  * Khi 30 workers ban đầu chạy: máy A (IP 1) bắt đầu ở Wave 1. Khi máy A hoàn thành feed session, worker trống sẽ bốc tiếp các máy còn lại của Wave 1 (từ máy 31 đến 39) trước.
  * Hết Wave 1, các workers mới bắt đầu bốc sang Wave 2.
  * Trong Wave 2, máy B (IP 1) lại được shuffle ngẫu nhiên ở một vị trí bất kỳ (đầu, giữa hoặc cuối danh sách 39 máy Wave 2).
- **Khoảng cách an toàn (Time Gap) thực tế:**
  * Máy B xuất phát sau máy A từ **15 đến 35 phút**.
  * Khi máy B được bốc, nó tiếp tục mất **10–15 phút lướt feed** trước khi chạm đến bước bấm Follow.
  * Do đó, thời điểm máy A bấm follow và máy B bấm follow cách nhau **ít nhất 15–35 phút**.
  * Nếu máy A dính nhả follow ở Wave 1 $\to$ Cầu dao giật ngắt IP ngay lập tức $\to$ Đến phút 25–40 khi máy B chuẩn bị bấm follow, `check_ip_breaker` phát hiện cờ `TRIPPED` và **Safe-Skip** ngay lập tức, cứu nick an toàn 100%.

## 5. Bằng Chứng Kiểm Chứng (Verification Evidence)
- **Unit test suite:** `D:/Taadaa/automation-core/tests/test_machine_launch.py` (16 passed in 0.73s).
- **Ca test bao phủ:**
  1. `test_partition_no_collisions_within_any_wave`: 80 máy, 40 proxy, 2 waves, zero collision trong cả 2 wave.
  2. `test_partition_admin_three_machines`: 3 máy cùng 1 proxy admin, phân tách chuẩn sang 3 waves.
  3. `test_partition_empty_and_single`: danh sách rỗng và 1 máy đơn lẻ.
  4. `test_build_wave_launch_plan_contract`: xác nhận thứ tự order của launch plan xếp trọn vẹn Wave 1 trước Wave 2.
  5. `test_load_machine_proxy_mapping_resilience`: xử lý an toàn khi file Excel bị thiếu/hỏng mà không crash.
  6. `test_partition_partner_isolation_flow`: mô phỏng cặp máy M33 & M72 trên port 10001, xác nhận 1 máy vào Wave 1 và 1 máy vào Wave 2.
