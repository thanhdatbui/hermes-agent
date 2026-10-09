# Targeted Canary vs Full Session Pitfall & Threshold Rules

## 1. Sự cố Canary Bounded (Chạy sai Entrypoint)
- **Triệu chứng**: Khi sửa một hàm cụ thể (ví dụ: `_open_following_tab`, selector tiếng Việt `Đang follow`, popup dismiss), agent/worker gọi nguyên lệnh chạy session/batch pipeline (như `run_follow.py --mode 2 --account-row-index 2`).
- **Hậu quả**:
  1. Pipeline nuôi acc chạy đầy đủ logic người dùng (lướt video, xem video, delay 15-18 follows) kéo dài >10-15 phút.
  2. Subagent chạm trần timeout (300-360s) bị kill giữa chừng.
  3. Báo cáo hoàn thành sai lệch và chụp ảnh màn hình non (mới ở màn hình tìm kiếm `Search landing`, chưa tới được màn hình đích cần kiểm chứng).
- **Quy tắc bắt buộc**:
  - **Canary BẮT BUỘC nhắm đúng function/hook vừa sửa** (`--canary-hook <tên_hàm>`, `--canary-target <uid>`, hoặc focused probe script độc lập <60s).
  - CẤM TUYỆT ĐỐI chạy full session/budget khi canary kiểm chứng logic hàm.
  - **Nghiệm thu ảnh MEDIA:** BẮT BUỘC chụp ảnh tại đúng màn hình kết quả sau khi hàm chạy xong (ví dụ: danh sách Following đã bung ra). Cấm chụp ảnh lúc máy mới mở trang tìm kiếm hoặc chưa vào màn hình đích.

## 2. Ngưỡng Báo Động Đỏ Farm Alert (>10 máy lỗi)
- **Ngưỡng quy định**: Khi tổng kết bất kỳ phiên/ca nuôi acc nào (Feed, Follow hook, Upload hook), nếu số lượng máy bị lỗi ở bất kỳ khâu nào **vượt quá 10 máy** (`> 10 máy`):
  - BẮT BUỘC phát tín hiệu báo động đỏ `[FARM ALERT]` về nhóm Telegram Farm Alert (`-5373649734`).
  - Không được để tỷ lệ lướt feed thành công che khuất tỷ lệ fail của các hook đi kèm (ví dụ Feed 67/80 OK nhưng Follow fail 13/14 máy vẫn là Mass Failure diện rộng).
