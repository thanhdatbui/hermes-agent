# Cạm Bẫy `--files` Trong Closeout Gate: Chỉ Truyền File Thực Sự Dirty

## 1. Hiện Tượng Lỗi (Symptom)
Khi gọi `closeout_gate.py` với cờ `--files` trên repository có nhiều file dirty từ các phiên trước:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/Hermes" --files deploy/hermes-home/scripts/tiktok_runner.py deploy/hermes-home/scripts/test_feed_session_watchdog.py --json-output
```
Hệ thống thoát ngay lập tức với `exit code 1` tại Step 2:
```text
══════════════════════════════════════════════════════════════════════
  STEP 2: EXTRACT CANDIDATE DIFF
══════════════════════════════════════════════════════════════════════
  ✘  Failed to extract diff: targets without working-tree changes: ['deploy/hermes-home/scripts/test_feed_session_watchdog.py']
```

## 2. Nguyên Nhân Kỹ Thuật (Root Cause)
- Cờ `--files PATH [PATH ...]` của `closeout_gate.py` được thiết kế theo cơ chế **Fail-Closed nghiêm ngặt**:
  Mọi đường dẫn file được liệt kê sau `--files` bắt buộc phải có diff thực tế trong working tree (`git diff` hoặc `git status -s`).
- Nếu một file chỉ được chạy test hoặc đọc tham chiếu nhưng **không bị chỉnh sửa trong phiên** (không có thay đổi mã nguồn), `closeout_gate.py` coi việc chỉ định file này là sai lệch phạm vi (scope mismatch) và từ chối trích xuất diff.

## 3. Quy Tắc Điều Phối Bắt Buộc Cho Coordinator
1. **Kiểm tra `git status --short` trước khi gọi Closeout Gate:**
   - Trước khi lập danh sách file cho `--files`, Coordinator bắt buộc đối soát danh sách target với output của `git status --short`.
2. **Loại bỏ triệt để file không dirty:**
   - CHỈ đưa vào `--files` các file có cờ `M`, `A`, hoặc `??` (được thêm mới) thực sự thuộc về task hiện tại.
   - TUYỆT ĐỐI KHÔNG đưa file test hoặc file phụ trợ vào `--files` nếu file đó không bị sửa đổi trong phiên làm việc.
3. **Cơ chế phát hiện Focused Test & Bẫy `--skip-test`:**
   - **CẤM TUYỆT ĐỐI dùng `--skip-test` trong repo mode:** `closeout_gate.py` sẽ chặn đứng vô điều kiện với lỗi `FATAL: --skip-test is forbidden in repo mode! Closeout Gate requires verified test execution.`
   - **Cơ chế ghép cặp Focused Test O(1):** `closeout_gate.py` tự động dò tìm file test tương ứng theo mẫu `tests/test_<stem>.py` (dựa trên tên file đích `<stem>.py`). Nếu tìm thấy, gate CHỈ chạy đúng test file đó (`pytest tests/test_<stem>.py -q`) trong < 2 giây.
   - **Bẫy Timeout Full-Suite:** Nếu file đích không có file test tương ứng dạng `tests/test_<stem>.py`, gate sẽ fallback về lệnh mặc định `pytest tests` quét toàn bộ hàng trăm test trong repo, dẫn tới nguy cơ timeout > 120s. Vì vậy, khi tạo/sửa file mới `<stem>.py`, BẮT BUỘC tạo kèm `tests/test_<stem>.py` để gate chạy focused test siêu tốc.
