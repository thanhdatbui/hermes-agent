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
3. **Chạy test cho file không sửa:**
   - Nếu muốn chạy test suite của file test không bị sửa, hãy để `closeout_gate.py` tự động phát hiện test hoặc chạy test độc lập trước khi kích hoạt closeout gate, không nhồi nhét file test sạch vào cờ `--files`.
