# Quy Chuẩn Báo Cáo Tiến Độ Upload Trên Watchdog Farm (Chống Gom Cục Mù Mờ)

## 1. Bối cảnh & Phản ánh từ Người vận hành (2026-09-19)
- **Triệu chứng:** Báo cáo watchdog tổng kết ca nuôi (ví dụ Ca 4 - Phiên 2/2) hiển thị dòng Đăng Video:
  ```text
  • Đăng Video (2/2 - 25 video đã đăng):
    + Success (25): 2, 4, 6, 11, 12, 14, 15, 16, 17, 18, 19, 21, 25, 29, 31, 34, 35, 38, 49, 59, 60, 61, 66, 69, 76
    + Timeout/Quá giờ (0): Không có
    + Lỗi script/xác minh (1): 77
    + Bỏ qua (42): Đang dưỡng sinh (16); Khác (26)
  ```
- **Người vận hành phản ánh:** *"Báo cáo gì đọc như cứt ấy chả biết cron up đc tới đâu"*.
- **Root Cause trong thiết kế báo cáo:**
  1. **Thiếu mẫu số chỉ số hoàn thành:** Chỉ ghi `25 video đã đăng` mà không ghi rõ trên tổng số bao nhiêu máy đủ điều kiện upload của ca (`25/26 [96.2%]`).
  2. **Mất thông tin lũy kế video number:** Không hiển thị tài khoản/máy đang đăng video số mấy (`v1`, `v2`, `v3`...), khiến người vận hành không nắm được tiến độ chu kỳ 30 ngày của dàn nick.
  3. **Gom cục mù mờ:** Dùng nhãn `Khác (26)` mà không liệt kê danh sách máy và phân rã nguyên nhân skip thực tế (tuổi nick <10 ngày, chưa render video, feed fail hủy upload).
  4. **Lỗi cụt lủn:** Ghi `Lỗi script/xác minh (1): 77` mà không kèm lý do ngắn gọn (lỗi UI xác minh, kẹt nút đăng, timeout).

---

## 2. Tiêu Chuẩn Báo Cáo Upload Mới (Actionable & Transparent)

Mọi báo cáo tổng kết phiên (`feed_session_watchdog.py`) hoặc cron upload BẮT BUỘC tuân thủ format sau:

```text
• Đăng Video ({phien}/2 - {up_success_cnt}/{up_eligible_cnt} máy đủ điều kiện [{percent}%]):
  + Thành công ({up_success_cnt}): M2(v1), M4(v2), M6(v1), M11(v1)...
  + Thất bại ({up_error_cnt}): M77 (Lỗi UI xác minh app)
  + Bỏ qua an toàn ({total_skip} máy):
    * Nghỉ dưỡng sinh ({rest_cnt} máy): M1, M5, M8, M9...
    * Nick ngâm < 10 ngày ({cooling_cnt} máy): M3, M10, M30...
    * Chưa có video render ({novideo_cnt} máy): M33, M36...
    * Hủy do feed fail ({feed_fail_cnt} máy): M68, M74...
```

---

## 3. Quy Tắc Phân Loại & Thu Thập Dữ Liệu

1. **Video Number Thu Thập Từ Receipt / Upload Ledger:**
   - Đọc `video_number` từ `upload_result.json` hoặc receipt JSON canonical (`machine_M_account_A_video_V.json`).
   - Format hiển thị gọn: `M<machine>(v<video_number>)`.

2. **Mẫu Số Máy Đủ Điều Kiện (`up_eligible_cnt`):**
   - `up_eligible_cnt = up_success_cnt + up_error_cnt + up_timeout_cnt`
   - Chỉ tính các máy thực sự được kích hoạt upload hook trong ca đó.

3. **Phân Rã 100% Nhóm Bỏ Qua (CẤM Gom "Khác"):**
   - Phải bóc tách tối thiểu 4 nhóm rõ ràng kèm danh sách máy:
     + `Nghỉ dưỡng sinh`: Do băm MD5 1/3 rơi vào ngày nghỉ lướt feed thuần.
     + `Nick ngâm < 10 ngày`: Tuổi nick chưa đạt mốc an toàn để up video.
     + `Chưa có video render`: Thư mục nguồn TikX chưa có file MP4 sẵn sàng.
     + `Hủy do feed fail`: Lướt feed thất bại hoặc crash app, fail-safe hủy upload.
