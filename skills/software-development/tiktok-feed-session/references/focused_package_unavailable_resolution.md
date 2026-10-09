# Xử Lý Lỗi "focused package unavailable" Trong TikTok Feed Session

## 1. Triệu chứng & Bối cảnh
- **Triệu chứng:** Phiên nuôi dừng với:
  - `status: fail`
  - `message: feed-session-smoke failed: focused package unavailable`
  - `stop_reason: focused package unavailable`
  ngay tại step `baseline` hoặc sau khi swipe/điều hướng, trong khi thực tế trên thiết bị TikTok feed vẫn đang hiển thị.
- **Môi trường hay gặp:** Các máy farm chạy đồng loạt, máy tải cao hoặc chuyển cảnh UI khiến WindowManager của Android phản hồi chậm.

## 2. Nguyên nhân gốc rễ
1. Hàm `get_focused_activity(ctx)` dùng `dumpsys window` để parse focused app/activity. Trong tích tắc khi activity đang chuyển đổi hoặc UI redraw, kết quả parse trả về `package: None`.
2. Trong `python_runner/core/safety.py`:
   ```python
   elif focus_pkg is None:
       return SafetyCheckResult(
           SAFETY_FAILED,
           "focused package unavailable",
           ...
       )
   ```
3. Trong `python_runner/flows/feed_swipe_smoke.py`:
   - Hàm `_row_from_attempt()` nhận `safety.status == SAFETY_FAILED` với reason `"focused package unavailable"`.
   - Nếu không có cơ chế re-poll / settle delay trước khi kết luận thất bại, attempt bị đánh dấu failed ngay lập tức và flow gán `stop_reason = "focused package unavailable"`.

## 3. Quy trình Fix chuẩn trong `feed_swipe_smoke.py`
1. **Graceful Focus Re-poll:**
   - Tại `_row_from_attempt()` hoặc trước khi finalize attempt thất bại:
     - Nếu `safety.reason == "focused package unavailable"`:
       - Chờ settle delay ngắn (1.0s – 1.5s).
       - Gọi lại `get_focused_activity(ctx)`.
       - Nếu package trả về thuộc `tiktok_pkgs` (`com.ss.android.ugc.trill`, v.v.), ghi đè lại `attempt["focused_package"]` và chạy lại `safety_check_attempt(attempt)`.
2. **Khai báo trong `_is_launcher_focus_loss()`:**
   - Đảm bảo `"package unavailable"` / `"focused package unavailable"` được xử lý như một dạng focus loss tạm thời có thể kích hoạt recovery ladder (re-launch hoặc settle re-poll) thay vì kết thúc terminal fail.

## 4. Pitfall điều tra log: Cấm quét đĩa / glob trên `.ai-runs`
- Thư mục `.ai-runs` chứa hàng trăm nghìn file artifacts (screenshot png, ui xml, jsonl).
- **CẤM** dùng `os.walk`, `glob("**/*.txt", recursive=True)` hoặc `grep` quét diện rộng vì sẽ timeout 15 phút (900s) và làm cạn kiệt số lượt gọi tool.
- **ĐÚNG:** 
  - Đọc trực tiếp đường dẫn run mới nhất bằng cách liệt kê danh sách folder cấp 1 và sắp xếp theo mtime (`os.listdir('.ai-runs')`).
  - Hoặc dùng script inspect tập trung: `python D:/Taadaa/tools/inspect_machine.py <N>`.
