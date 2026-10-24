# Closed-Loop Incident Auto-Harness & Autonomous Triage Pipeline (2026-10-24)

> Core Modules: `D:/Taadaa/tools/incident_envelope.py`, `D:/Taadaa/tools/incident_lock.py`, `D:/Taadaa/tools/incident_auto_harness.py`, `D:/Taadaa/tools/telegram_report.py`.

## 1. Bối cảnh & Mục tiêu Vận hành
- **Vấn đề cốt tử:** Operator mệt mỏi vì phải đóng vai trò router thủ công (nhận report ca chạy -> ném vào chat Telegram cho Hermes -> chờ LLM điều tra fix script).
- **Mục tiêu:** Chuyển dịch toàn bộ sang **Closed-Loop Autonomous Operations**. Watchdog ca chạy/chu kỳ tự động emit incident -> Headless Auto-Harness tự động bốc vé xử lý qua toàn bộ 6 Gate cơ học -> Tự commit/canary -> Bắn báo cáo Telegram kèm ảnh nghiệm thu ngay lập tức về đúng nhóm repo.

## 2. Chuẩn hoá Gói Sự Cố (`IncidentEnvelope`)
- **Vị trí hàng đợi:** `D:/Taadaa/runtime/incidents/pending/<incident_id>.json`.
- **Cấu trúc bắt buộc:**
  ```json
  {
    "incident_id": "uuid4",
    "source_watchdog": "tên_watchdog_phát_hiện.py",
    "repo": "D:/Taadaa/repo_name",
    "target_file": "path/to/target.py",
    "error_type": "ScriptExecutionError",
    "stack_trace": "...",
    "telemetry": {
      "xml_dump": "path/to/dump.xml",
      "screenshot": "path/to/screen.png",
      "log_tail": "..."
    },
    "error_signature": "sha256(error_type + target_file + top3_frames)[:16]",
    "telegram_chat_id": "-100..."
  }
  ```

## 3. Cơ Chế Khóa Chống Xung Đột NTFS (`IncidentLock`)
- **Nguyên tử trên Windows NTFS:** Sử dụng `os.open(..., O_CREAT | O_EXCL)`.
- **Phạm vi khóa (Scope Hash):** `sha256(repo + sorted(target_files))`.
  - 2 sự cố sửa khác file trong cùng repo: **Được phép chạy song song**.
  - 2 sự cố sửa trùng file: Tiến trình 2 nhận `BlockingIOError`, incident tự động nằm lại hàng đợi `pending/` để chờ sweep sau.
- **Stale-lock Cleanup:** Tự động dọn lock nếu PID sở hữu đã chết (`psutil.pid_exists(owner_pid) == False`) hoặc vượt quá TTL (mặc định 1800s).

## 4. Chuỗi 6 Cổng Điều Phối Cơ Học (`IncidentAutoHarness`)
Harness chạy trong một **Headless Process riêng biệt** (cấm chạy chung context của Coordinator), tuần tự qua 6 cổng:

1. **Cổng 0 — Telemetry Completeness Gate:**
   - Đánh giá `completeness_score`: XML phải đọc được + Screenshot phải tồn tại và đúng định dạng PNG/JPEG.
   - Nếu `score < 2`: Đánh dấu `BLOCKED_PENDING_TELEMETRY`, **CẤM TUYỆT ĐỐI sửa code nghiệp vụ mò mẫm**. Tự động tạo meta-task vá watchdog để bổ sung lệnh dump trước.
2. **Cổng 1 — Mechanical Planner Gate:**
   - Gọi trực tiếp `dispatch_planner.py`.
   - **Tier 1 (Mặc định):** Claude Sonnet CLI (`claude_worker.py --role planner`).
   - **Tier 2 (Fallback khi quota 5h >= 85%):** Sol Planner (:20129).
3. **Cổng 2 — O(1) Surgery Worker Gate:**
   - Gọi `dispatch_worker.py` thi công bản vá O(1) với giới hạn cứng: `<= 30 dòng diff`, `<= 2 files`.
4. **Cổng 3 — Protected Regression Gate:**
   - Chạy `guardgate/runner.py` đối soát hằng số bất biến (Case 162 connection timeout >= 20s, Case 161 follow ceiling...). Vi phạm -> REVERT ngay lập tức.
5. **Cổng 4 — Canary Gate:**
   - Kiểm tra `canary_evidence.json` và file media ảnh thực tế trên máy rảnh.
6. **Cổng 5 — Closeout Gate:**
   - Chạy `closeout_gate.py`.
   - Kiểm tra chặt chẽ `res.returncode == 0` và Reviewer Sol (:20129) chấm điểm `>= 85/100` (hoặc Grace Band 80–84 có test xanh).
   - Thất bại hoặc lỗi cú pháp JSON -> REJECT, không bao giờ tự đóng ticket.

## 5. Báo Cáo Nghiệm Thu Tức Thì (`telegram_report.py`)
- Định tuyến tự động theo nhóm:
  - Repo Nuôi acc: `-5377611430`
  - Repo Video/Render: `-5435853713`
  - Mặc định / Farm Alert: `-5373649734`
- Bắt buộc gửi kèm ảnh thực tế qua `MEDIA:<path>` ngay sau khi Cổng 5 APPROVED.
