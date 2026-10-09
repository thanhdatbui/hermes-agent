# Watchdog Follow Failed Reconciliation Skew & Phantom Discrepancy (+22)

## 1. Hiện tượng & Triệu chứng (2026-10-03)
Khi kết thúc ca nuôi (Ca 1 Sáng - Row 1), báo cáo watchdog hiển thị con số lệch lớn:
```text
  + Đối soát TikTok Web (+95 Following thật | Lệch +22 so với script báo 73):
    - M16 (@nhuphuong458934): script báo 8 (chéo 8, tự nhiên 0) | web tăng +9 (Lệch +1)
    - M37 (@ngc.trinh6472): script báo 10 (chéo 7, tự nhiên 3) | web tăng +11 (Lệch +1)
    - M52 (@vy.nguyen8730): script báo 0 (chéo 9, tự nhiên 3) | web tăng +12 (Lệch +12)
    - M62 (@minh.anhhhh85): script báo 0 (chéo 0, tự nhiên 1) | web tăng +1 (Lệch +1)
    - M70 (@nh.bi547): script báo 0 (chéo 4, tự nhiên 2) | web tăng +6 (Lệch +6)
    - M71 (@ngc.anh.phm33): script báo 0 (chéo 0, tự nhiên 2) | web tăng +1 (Lệch +1)
  + Nhả follow (18 máy):
    - Nhả liền (0 lượt - 15 máy): M11, M15, M21, M25, M27, M32, M34, M42, M47, M48, M58, M62, M63, M71, M76
    - 1 - 4 lượt (2 máy): M57 (1 lượt), M70 (4 lượt)
    - 5 - 9 lượt (1 máy): M52 (9 lượt)
```
Người vận hành chất vấn: *"Ủa sao lệch nhiều v"*.

## 2. Root Cause Analysis
Phân tích chi tiết dữ liệu snapshot trong `tiktok_tracker.db` và artifact `follow_result.json`:

1. **Khớp thực tế ngoài đời 100%:**
   - **M52 (@vy.nguyen8730):** Bấm thành công 9 lượt follow chéo và 3 lượt follow tự nhiên. Đến lượt thứ 10, TikTok không nhận nút follow -> script kích hoạt chốt an toàn dừng phiên và trả về `status: FOLLOW_FAILED`, `follow_failed: True`, `followed: [9 uids]`.
   - Trên TikTok Web, tài khoản tăng từ 122 lên 134 (+12 following). TikTok KHÔNG hề rollback hay nhả 12 lượt đã bấm trước đó!
   - 9 chéo + 3 tự nhiên = 12, khớp 100% với Web tăng +12.
   - **M70 (@nh.bi547):** Bấm thành công 4 chéo + 2 tự nhiên = 6 lượt. Đến lượt thứ 5 bị nhả sau re-entry -> dừng session với `followed: [4 uids]`. Trên TikTok Web tăng từ 214 lên 220 (+6 following). Khớp 100%.
   - **M62 (@minh.anhhhh85):** Follow chéo 0, follow tự nhiên 1 -> Web tăng +1. Khớp 100%.
   - **M71 (@ngc.anh.phm33):** Follow chéo 0, follow tự nhiên 2 -> Web tăng +1 (hoặc +2 tùy độ trễ).

2. **Khiếm khuyết logic trong `feed_session_watchdog.py`:**
   - Tại commit `33ce05202b1da5496fbf641f7b539b695b79a25a`, tác giả muốn tránh trường hợp máy fail bị âm delta khi TikTok nhả follow sạch (`0 - cnt = -cnt`), nên đã thêm dòng:
     ```python
     # A machine that failed/released its follows must not create a negative web reconciliation delta
     m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt
     ```
   - Hậu quả nghiêm trọng:
     - Khi `failed == True`, code ép cứng `m_to_reported = 0`.
     - `natural_cnt` (follow tự nhiên khi lướt feed diễn ra trước đó và đã thành công) bị xóa sạch về 0.
     - `cnt` (danh sách tài khoản đã follow chéo thành công TRƯỚC KHI dính lỗi ở lượt sau) cũng bị xóa sạch về 0.
     - Watchdog so sánh `web_delta` (+12) với `expected_delta` (0) -> tạo ra **lệch dương ảo +12** cho M52, **+6** cho M70, **+1** cho M62, **+1** cho M71. Tổng cộng tạo ra **+20 lượt lệch ảo** trong tổng số +22 lượt lệch!
     - Dòng chữ in ra trở nên nghịch lý: `script báo 0 (chéo 9, tự nhiên 3) | web tăng +12 (Lệch +12)` (vừa ghi đã bấm 9+3=12, nhưng lại bảo script báo 0 và lệch 12).

## 3. Bản chất phân loại "Nhả follow"
- Trong `classify_machine_follow_result`: Bất kỳ kết quả nào có `status == "FOLLOW_FAILED"` và `follow_failed is True` đều bị xếp vào nhóm `fl_released` ("Nhả follow").
- Tuy nhiên cần phân biệt:
  - **Nhả liền (0 lượt):** Bấm ngay nick đầu tiên đã bị drop -> thực sự 0 lượt thành công.
  - **Bị ngắt phiên giữa chừng (N lượt):** Đã follow thành công N lượt trước đó, chỉ dừng ở lượt N+1. Các lượt 1..N vẫn được TikTok ghi nhận đầy đủ trên Web.

## 4. Giải pháp & Quy chuẩn (Chính Sách Người Dùng Chốt 2026-10-03)
Khi tài khoản dính cờ `follow_failed` / `fl_released`:
1. **Trường hợp lượt đầu tiên follow chéo = 0 (`cnt == 0`):**
   - Vừa bấm lượt đầu đã bị nhả/drop (hoặc không nhận nút) -> Nick đã bị Silent Action Block từ sớm -> Bỏ hết cả follow tự nhiên và chéo:
     `m_to_reported[str(m)] = 0`
   - Đồng thời, hàm `calculate_session_natural_follows` tự động khấu trừ toàn bộ follow tự nhiên của máy này ra khỏi tổng phiên để tránh lệch âm.
2. **Trường hợp lượt đầu tiên follow chéo thành công (`cnt > 0`):**
   - Nick không bị Action Block lúc lướt feed, đã hoàn tất toàn bộ follow tự nhiên và bấm thành công `cnt` lượt chéo trước khi bị ngắt ở lượt N+1:
     - Tính hết 100% follow tự nhiên thành công (`natural_cnt`).
     - Bắt đầu bộ đếm cho tới khi bị nhả: tính đúng `cnt` lượt chéo đã gửi lên server.
     - Tổng script báo: `m_to_reported[str(m)] = cnt + natural_cnt`.
     - Tuyệt đối KHÔNG trừ follow tự nhiên của máy này trong `calculate_session_natural_follows`.
   - Kết quả: Web tăng thật (+12 với M52, +6 với M70) khớp 100% với script báo (12 và 6), xóa bỏ hoàn toàn +20 lượt lệch dương ảo!
