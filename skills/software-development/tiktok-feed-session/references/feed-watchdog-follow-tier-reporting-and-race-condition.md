# Chuẩn Hóa Báo Cáo Follow Chéo Theo Nhóm Lượt & Cơ Chế Chống Chốt Sớm Trong Watchdog

## 1. Bối cảnh & Yêu cầu của User (09/09/2026)
- Khi watchdog tổng kết phiên nuôi acc TikTok (`feed_session_watchdog.py`), mục **• Follow chéo** trước đây chỉ gom nhóm cho `Nhả follow`, còn mục `Success` bị bỏ quên dưới dạng danh sách máy thô (`+ Success (N): 2, 9, 20...`) không có dải lượt và không có số lượt follow của từng máy.
- User phản ánh: *"Bữa t làm báo cáo là khi ghi kết quả follow phải kèm theo từng nhóm r mà"*.
- **Quy chuẩn bất biến:** CẢ 2 mục `Success` và `Nhả follow` đều BẮT BUỘC phải phân nhóm theo từng dải lượt:
  + Dải 1 – 4 lượt: Liệt kê `M<máy> (<cnt> lượt)`
  + Dải 5 – 9 lượt: Liệt kê `M<máy> (<cnt> lượt)`
  + Dải 10+ lượt: Liệt kê `M<máy> (<cnt> lượt)`
  + Riêng `Nhả follow` có thêm dải: `Nhả liền (0 lượt - X máy): M<máy>...`

## 2. Mẫu Báo Cáo Follow Chuẩn
```text
• Follow chéo (85 lượt follow):
  + Success (8 máy):
    - 1 - 4 lượt (1 máy): M70 (3 lượt)
    - 5 - 9 lượt (2 máy): M20 (6 lượt), M9 (8 lượt)
    - 10+ lượt (5 máy): M2 (12 lượt), M21 (10 lượt), M36 (11 lượt), M40 (11 lượt), M72 (10 lượt)
  + Nhả follow (15 máy):
    - Nhả liền (0 lượt - 10 máy): M10, M18, M19, M25, M27, M28, M29, M39, M50, M63
    - 1 - 4 lượt (4 máy): M6 (2 lượt), M8 (1 lượt), M49 (1 lượt), M59 (1 lượt)
    - 5 - 9 lượt (1 máy): M38 (9 lượt)
  + Lỗi script/xác minh (1): M74
  + Bỏ qua (53 máy): 1, 3, 4, 5, 7, 42, ...
```

## 3. Hai Cạm Bẫy Cần Tránh Trong Watchdog Nuôi Acc
1. **Cạm bẫy Race Condition chốt sớm (`can_report_session`):**
   - Nếu kiểm tra `completed_expected_count >= expected_count` trước khi kiểm tra `runner_busy`, watchdog sẽ chốt báo cáo ngay khi các máy vừa lướt Feed xong, trong khi tiến trình Follow hook nối đuôi vẫn đang chạy (ví dụ máy 21 mất thêm 5 phút chạy follow).
   - Hậu quả: Máy đang chạy follow chưa kịp ghi `follow_result.json` sẽ bị watchdog tính nhầm thành `Lỗi script/xác minh`.
   - **Cách khắc phục:** Trong giờ phiên (`is_today and now_hm < window_end_hm`), nếu `runner_busy is True` thì BẮT BUỘC trả về `False` để chờ toàn bộ follow hooks hoàn tất.

2. **Cạm bẫy phân loại nhầm máy 0 follow do skip target thành lỗi:**
   - Khi máy có `status in {"OK", "SUCCESS"}` nhưng `followed_count == 0` (do các target search bị skip, không tìm thấy hoặc đã follow trước đó), máy này không gặp lỗi script hay xác minh.
   - **Cách khắc phục:** Phải phân loại vào `fl_skipped` (Bỏ qua), không được để rơi vào nhánh `else: fl_error.append(m)`.
