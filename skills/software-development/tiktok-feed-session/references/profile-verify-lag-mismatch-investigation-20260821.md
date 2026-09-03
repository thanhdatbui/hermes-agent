# Chẩn đoán lỗi Profile Verification Mismatch & False Alarm do Lag chuyển cảnh (2026-08-21)

## Bối cảnh & Hiện tượng (Sự cố Máy 15 - Ca Feed Session row-1)
- Script: `multi-machine-feed-session` / `feed-session-smoke`.
- Quá trình lướt video (`swipe`): Đã hoàn thành 100% (18/18 lượt swipe đều success).
- Lỗi phát sinh ở bước cuối: `verify_profile` sau khi gọi `tap_profile` điều hướng về màn hình Hồ sơ cá nhân.
- Thông báo Telegram: `🚨 [MÁY 15] DỪNG PHIÊN - Lý do: profile verification mismatch: profile account mismatch`.

## Nguyên nhân gốc (Root Cause qua phân tích log.jsonl & XML)
1. **Lag chuyển cảnh UI của TikTok (S7 / Android yếu)**:
   - Khi `tap_navigation_target(profile)` thành công, TikTok bắt đầu chuyển từ Home Feed sang Hồ sơ.
   - Script gọi `_capture_xml_text(ctx, "verify_profile")` ngay lập tức.
   - Tại thời điểm dump XML, cây DOM mới chỉ render được một phần text phía dưới (ví dụ nút "Thêm tiểu sử"), còn node chứa username `@h.h67426` chưa kịp nạp lên UI tree (`profile_username: None`).
2. **Khuyết thiếu cơ chế Bounded Retry / Wait for Profile UI**:
   - Hàm `_verify_profile_after_session()` chỉ parse XML 1 lần duy nhất mà không có vòng lặp chờ `@username` xuất hiện hoặc timeout ngắn (1.5–2s) khi thấy thiếu username.
   - Do đó, so khớp `matched = any(expected == value for value in normalized)` trả về `False` $\rightarrow$ Đánh giá nhầm là sai nick (*false mismatch*).

## Cách xử lý & Quy chuẩn Đã Triển Khai
- **Hành vi của Auto-Recovery**:
  1. Kiểm tra màn hình qua ADB / vision: xác nhận không bị kẹt popup/dialog/crash.
  2. Xác nhận nick đang đăng nhập trên máy thực tế khớp đúng với Excel.
  3. Kích hoạt tiếp tục hoặc chuyển giao an toàn mà không cần can thiệp thủ công.
- **Bản vá code `feed_swipe_smoke.py` (Commit `e337d2f`)**:
  - Tại hàm `_verify_profile_after_session()`, khi không khớp username ở lần đọc XML đầu tiên, script tự động `time.sleep(1.5)` và chụp lại XML lần 2 (`{artifact_prefix}_profile_retry`) để đối soát lại trước khi đưa ra kết luận `mismatch`.
  - Có test TDD bảo vệ: `test_verify_profile_after_session_retries_on_profile_lag`.
