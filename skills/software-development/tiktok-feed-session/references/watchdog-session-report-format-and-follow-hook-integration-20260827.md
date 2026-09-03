# Quy Chuẩn Báo Cáo Phiên Nuôi Acc & Tích Hợp Follow Hook (2026-08-27)

## 1. Yêu Cầu & Định Dạng Báo Cáo Phiên (User Correction 27/08)
- **CẤM hiển thị mẫu số cố định / dự đoán dạng `X / Y máy`**: User bắt buộc báo cáo phải hiển thị chính xác số lượng máy thực tế được xử lý trong phiên (`• Tổng máy xử lý: N máy`).
- **Tích hợp báo cáo Follow Hook trực tiếp vào Báo Cáo Phiên**: Sau mỗi phiên nuôi (khi cả Feed và Follow hoàn tất), watchdog `feed_session_watchdog.py` tự động tổng hợp cả kết quả Lướt Feed và Follow chéo.

## 2. Mẫu Báo Cáo Chuẩn (User Correction 2026-08-27)
```text
📊 [TIKTOK NUÔI ACC] Ca 1 - Phiên 3/3 (Sáng) hoàn tất (Row 1)
• Tổng máy xử lý: 74 máy
• Lướt Feed:
  + Success (69): 1, 2, 3, 4, 5, 6, 7, 8, 9, ...
  + Fail (5): M39, M41, M46, M69, M73
• Follow chéo (57 lượt follow):
  + Success (12): 1, 3, 5, 8, ...
  + Nhả follow (0): Không có
  + Lỗi script/xác minh (19): 2, 4, 6, 7, ...
  + Bỏ qua (5): 10, 15, 20, ...
```

## 3. Cơ Chế Thu Thập & Phân Loại Follow Hook
1. **Lướt Feed**: Đọc toàn bộ `summary.txt` trong các folder run (`row-X-HHMMSS`) thuộc khung giờ phiên. Lọc `final_status: success` -> nhóm Success; còn lại -> nhóm Fail.
2. **Follow Hook**: Đọc toàn bộ `follow_result.json`.
   - **Nhả Follow (`FOLLOW_FAILED`)**: Chỉ tính khi có status `FOLLOW_FAILED` do verifier xác nhận sau khi tap/refresh mà nút quay lại Follow. CẤM gán nhầm exit code 1 hoặc `MANUAL_REVIEW` thành nhả follow.
   - **Lỗi script/xác minh**: `MANUAL_REVIEW`, `TIMEOUT`, exit code 1, không tìm thấy profile/nút Follow...
   - **Bỏ qua (`SKIPPED`)**: 0 video, daily cooldown, sensitive-skip, warmup row.
   - **Success**: Status `OK`/`SUCCESS` và có `len(followed) > 0`.
3. **Quy tắc Warmup Tik 3..6 (Row 3..6)**:
   - Trong 14 ngày đầu nuôi acc, nick thuộc Row 3..6 (Tik3..6) chỉ lướt feed nuôi acc, tuyệt đối không chạy tool follow. Follow hook tự động skip với `reason: tik{row}-warmup-feed-only`.
4. **Cơ Chế Gửi Báo Cáo (No Spam)**:
   - Chỉ gửi đúng 1 lần khi toàn bộ máy trong ca/phiên đã hoàn tất hoặc phiên hết giờ và không còn tiến trình runner/follow nào đang chạy (`not is_feed_runner_active()`).
   - Lưu trạng thái vào `feed_session_reported.json` để chống gửi lặp lại.
