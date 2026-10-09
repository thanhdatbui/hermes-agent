# Phân tích sự cố: Test Suite bắn Spam Telegram thật & Zombie Stale Summary (2026-09-24)

## 1. Hiện tượng & Triệu chứng
- Trên nhóm Telegram Farm Alerts (`-5373649734`), liên tục xuất hiện 3 tin nhắn giống nhau báo kết quả Preflight Reg Bù trong vòng vài phút (06:59:53, 07:02:22, 07:03:13).
- Nội dung tin nhắn bất thường:
  - Header: `📋 [PREFLIGHT REG BÙ ROW 5]` (Row 5 ca tối) nhưng lại gửi vào lúc 07:00 sáng.
  - Body: Báo `❌ Thất bại: Máy 76: [04_add_account] Máy đã có 8 tài khoản` kết hợp với `⏸️ Bỏ qua / Cooldown (1): 201`.
  - Thực tế: Máy 76 thuộc cụm Kibe (Row 2), Máy 201 thuộc cụm Admin. Không có lệnh batch thật nào đang chạy tại thời điểm đó.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Thiếu Isolation trong Unit Test (Test Side-Effects):**
   - Trong `D:/Taadaa/tools/tests/test_ensure_row_accounts.py`, test case `test_admin_adb_socket_telemetry` gọi hàm thực thi batch `era.run_tiktok_reg_for_machines([201], row=5, max_workers=1)`.
   - Test case chỉ mock `subprocess.run` nhưng quên mock `send_telegram_summary` / `requests.post`.
   - Mỗi lần developer / agent chạy `pytest D:/Taadaa/tools` để kiểm tra code, request POST HTTP thật được gửi trực tiếp đến Telegram Bot API.

2. **Zombie Stale Artifact Summary (Logic lỗi lấy log cũ):**
   - Trong `send_telegram_summary`, code tìm log folder mới nhất bằng cách duyệt đĩa:
     ```python
     dirs = sorted(runs_dir.glob("20*"), key=lambda d: d.stat().st_mtime, reverse=True)
     latest_run = dirs[0]
     ```
   - Do batch test không tạo ra folder log mới, script tự động nhặt folder mới nhất hiện có trên đĩa là run `20260924-060255` (đợt chạy của Máy 76 lúc 06:02 sáng).
   - Script ghép log lỗi của Máy 76 từ quá khứ với tham số `missing=[201]` của test case hiện tại, sinh ra alert dị thường.

## 3. Quy tắc phòng chống bất biến (Invariants)
1. **Hard Guard chặn HTTP Telemetry trong môi trường Test:**
   - Trong mọi script viễn trắc/thông báo (`send_telegram_*`, webhook, bot alert), BẮT BUỘC chèn chốt chặn:
     ```python
     if disable_telegram or "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
         print("[telemetry] [TEST ENV] Skipped external notification during test execution.")
         return False
     ```
2. **Mock triệt để side-effect trong test cases:**
   - Trong file test, mọi hàm gọi đến runner/batch cấp cao BẮT BUỘC phải mock rõ ràng các hàm notify/alert:
     ```python
     monkeypatch.setattr(module, "send_telegram_summary", lambda *a, **kw: None)
     ```
3. **Chống Zombie Stale Artifacts (Time-gated run log selection):**
   - Tuyệt đối không chỉ lấy `dirs[0]` trần trụi.
   - BẮT BUỘC đối soát mtime của run folder với `batch_start_time`:
     ```python
     if batch_start_time is not None:
         min_ts = batch_start_time.timestamp() - 10
         dirs = [d for d in dirs if d.stat().st_mtime >= min_ts]
         if not dirs:
             return False # Không có run mới, bỏ qua summary
     ```
