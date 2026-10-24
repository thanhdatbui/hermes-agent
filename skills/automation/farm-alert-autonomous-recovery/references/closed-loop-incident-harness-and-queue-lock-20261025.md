# Closed-Loop Incident Auto-Heal Harness & Queue Lock (2026-10-25)

## 1. Kiến Trúc Khép Kín 6 Cổng (Closed-Loop Auto-Heal)
Tự động hóa hoàn toàn quy trình xử lý sự cố script/UI drift cho farm mà không cần Operator ném log thủ công:
- **Cổng 0 (Telemetry Completeness Gate):** Bắt buộc `completeness_score == 2` (có XML đọc được và ảnh chụp màn hình định dạng PNG/JPEG > 0 byte). Thiếu bằng chứng -> `BLOCKED_PENDING_TELEMETRY`, cấm sửa mò.
- **Cổng 1 (Mechanical Planner Gate):** Bắt buộc gọi `dispatch_planner.py` (Claude Sonnet CLI Tier 1, Sol Planner Tier 2 khi quota 5h >= 85%).
- **Cổng 2 (O(1) Surgery Worker Gate):** Gọi `dispatch_worker.py` thi công bản vá O(1) <= 30 dòng diff, <= 2 files.
- **Cổng 3 (Protected Regression Gate):** Chạy `guardgate/runner.py` kiểm tra hằng số bảo vệ (Case 162 timeout >= 20s, Case 161 follow ceiling <= 0).
- **Cổng 4 (Canary Verification Gate):** Kích hoạt `canary_runner.py` trên máy test rảnh và kiểm tra receipt ảnh thực tế.
- **Cổng 5 (Closeout Gate):** Chạy `closeout_gate.py` qua Reviewer Sol (:20129) với điều kiện tiên quyết `res.returncode == 0` và điểm số >= 85 (hoặc Grace Band >= 80).

## 2. Khóa An Toàn Theo File/Scope Trên Windows NTFS (`incident_lock.py`)
- Khóa theo `scope_hash = sha256(repo + sorted(target_files))` dùng cờ `os.O_CREAT | os.O_EXCL` nguyên tử.
- Hai sự cố sửa khác file chạy song song an toàn; sự cố trùng file tự động xếp hàng, không bao giờ đè diff hay kẹt `.git/index.lock`.
- Stale Lock Cleanup: Kiểm tra TTL (1800s) và `psutil.pid_exists(owner_pid)`. Trước khi xóa stale lock, bắt buộc re-check nội dung để tránh xóa nhầm lock mới do tiến trình khác vừa tạo.
- Release Lock: Đối chiếu cả `owner_pid`, `incident_id` và `host` trước khi xóa file lock.

## 3. Chống Bão Sự Cố (Incident Coalescing)
- Khi 15 máy trong ca cùng gặp 1 popup mới của TikTok, nếu không gom lỗi sẽ dội bom hàng đợi.
- Dùng marker nguyên tử `SIG_{error_signature}.marker` với TTL 20 phút (1200s khớp 1 ca chạy):
  - Máy đầu tiên tạo marker và mở 1 ticket duy nhất cho LLM sửa.
  - Các máy tiếp theo trong cửa sổ TTL chỉ bổ sung `machine_id` vào `affected_machines.jsonl`, không tạo ticket mới.

## 4. Báo Cáo & Vận Hành Định Kỳ
- `cron_incident_auto_heal.py` chạy mỗi 15 phút (`*/15 * * * *`) ở chế độ `no_agent=True` (im lặng tuyệt đối khi không có lỗi).
- `telegram_report.py` tự động định tuyến thông báo nghiệm thu kèm `MEDIA:<path>` về đúng nhóm theo repo (Nuôi `-5377611430`, Video `-5435853713`, Alert `-5373649734`).
