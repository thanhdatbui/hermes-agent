# Closed-Loop Incident Harness, Scope Locking, and Telemetry Completeness Gate

> Core Concept: Tái hiện 1:1 quy trình xử lý của Operator bằng Mechanical Auto-Harness. Không để thiết bị treo màn hình chờ LLM; không sửa code mù khi thiếu telemetry; serialize concurrency theo tập file thay đổi.

## 1. Không Treo Máy Chờ LLM (Zero-Hang on Error)
- **Sai lầm (Pitfall):** Bắt điện thoại kẹt ở màn hình lỗi để chờ LLM phẫu thuật code (60–180s) sẽ gây hết phiên app (session timeout), quá nhiệt, hoặc watchdog khác nhảy vào kill máy.
- **Thực hành chuẩn:**
  1. Khi phát hiện kẹt / exception, máy dump O(1) telemetry: Screenshot + UI XML dump + stack trace.
  2. Không force-stop app ngay trước khi kiểm tra popup (tắt app làm mất dấu vết XML và không dọn được popup hệ thống).
  3. Sau khi dump telemetry xong, máy trả về Home an toàn, nhả device-lock để ca chạy tiếp tục hoặc nhường tài nguyên.
  4. Lỗi được đóng gói thành `IncidentEnvelope` (`incident_envelope.py`) và đẩy vào hàng đợi `runtime/incidents/pending/`.

## 2. Telemetry Completeness Gate (Cổng 0: Chống Sửa Mò)
- **Quy tắc:** `completeness_score = (có XML đọc được) + (có ảnh chụp screenshot > 0 bytes)`.
- **Nếu `score < 2` (Thiếu XML hoặc ảnh):**
  - CẤM TUYỆT ĐỐI gọi LLM (Claude/Sol) sửa code nghiệp vụ.
  - Tự động tạo Meta-Incident: Yêu cầu sửa chính script watchdog đó để bổ sung đoạn mã dump UI XML và chụp screenshot vào khối `except`.
  - Bản vá bổ sung telemetry vẫn phải tuân thủ nghiêm ngặt các gate (Plan -> Worker <= 30 dòng -> Closeout Gate >= 85).

## 3. Concurrency & Scope-Level Locking trên Windows NTFS
- Khi 2 watchdog cùng lúc phát sinh lỗi, việc can thiệp code phải tránh race condition và kẹt `.git/index.lock`:
  - **Khóa File-Scope (`incident_lock.py`):** Khóa theo `scope_hash = sha256(repo + sorted(target_files))` bằng `os.open(..., O_CREAT | O_EXCL)`.
  - Hai incident sửa các file khác nhau trong cùng repo: Được phép chạy song song.
  - Hai incident chạm cùng file: Incident thứ 2 nhận lock bận (`EEXIST`) và tự động nằm lại trong `pending/`.
  - **Stale Lock Cleanup:** Nếu lock quá TTL hoặc PID sở hữu đã chết (`psutil.pid_exists`), lock mới tự động dọn stale lock để tiếp quản.
  - **Git index lock:** Tái sử dụng `closeout_gate.sanitize_repo()` (kiểm tra `LOCK_STALE_AGE` 10s + xác nhận git writer process chết hẳn trước khi unlink).

## 4. Pipeline Điều Phối Khép Kín (Closed-Loop Anti-Skipping Harness)
- Thực thi hoàn toàn trong tiến trình con cô lập (Headless Subprocess `incident_auto_harness.py`), không làm phình hay lag session chính.
- Bắt buộc qua 6 cửa ải tuần tự:
  1. `GATE_0_TELEMETRY`: Kiểm tra XML + Ảnh. Thiếu -> Tạo task vá watchdog dump.
  2. `GATE_1_PLANNER`: Gọi `dispatch_planner.py` (Claude Sonnet Tier 1, Sol Tier 2) -> Bắt buộc sinh `plan.json` có anchor `grep -c == 1`.
  3. `GATE_2_WORKER`: Gọi `dispatch_worker.py` thi công bản vá O(1) <= 30 dòng diff, <= 2 files.
  4. `GATE_3_REGRESSION`: Chạy `guardgate` so khớp diff với `protected_constants.json` (chống sửa ngược Case 162...).
  5. `GATE_4_CANARY`: Chạy `canary_runner.py` trên 1 thiết bị/nick độc lập lấy receipt thực tế.
  6. `GATE_5_CLOSEOUT`: Chạy `closeout_gate.py` với Sol Reviewer (:20129) chấm điểm. Chỉ commit `[auto-heal]` khi điểm >= 85/100.
- Sau khi đóng dấu thành công: Bắn báo cáo Telegram thời gian thực kèm `MEDIA:<canary_image>` và điểm review về đúng group của repo.
