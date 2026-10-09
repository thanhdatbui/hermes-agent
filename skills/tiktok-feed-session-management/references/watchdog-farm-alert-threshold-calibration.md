# Hiệu Chỉnh Ngưỡng Cảnh Báo Farm Alert & Chống Báo Động Giả Lỗi Hàng Loạt (Watchdog)

## 1. Hiện Tượng & Phản Hồi Người Vận Hành (2026-10-03)
- **Thông báo từ Watchdog**:
  ```text
  🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (3 máy lỗi script Upload) - Ca 1 - Phiên 2/2 (Sáng) (Row 1)
  ...
  • Đăng Video (2/2 - 39 video đã đăng):
    + Success (39): 1, 2, 3, 7, 9, 11, 12, 15, 16, 18, 21, 25, 27, 31, 32, 33, 34, 38, 39, 40, 43, 47, 48, 51, 52, 56, 57, 58, 60, 61, 62, 63, 64, 68, 70, 71, 76, 78, 80
    + Timeout/Quá giờ (0): Không có
    + Lỗi script/xác minh (3): 19, 37, 42
    + Bỏ qua (35): Đang dưỡng sinh (34); Khác (1)
  ```
- **Người vận hành chất vấn**: *"là sao lỗi có 3 máy báo chi v"*.

---

## 2. Nguyên Nhân Cốt Lõi (Root Cause)
1. **Ngưỡng Hardcode Quá Thấp trong Code (`feed_session_watchdog.py`)**:
   - Trước đây trong đoạn logic gán `header`:
     ```python
     tot_fl_err = sum(len(b.get("fl_error", [])) for b in cluster_stats) if 'cluster_stats' in locals() else len(fl_error)
     tot_up_err = sum(len(b.get("up_error", [])) for b in cluster_stats) if 'cluster_stats' in locals() else len(up_error) + len(up_timeout)
     if tot_fl_err >= 3:
         has_script_alert = True
         alert_reasons.append(f"{tot_fl_err} máy lỗi script Follow")
     if tot_up_err >= 3:
         has_script_alert = True
         alert_reasons.append(f"{tot_up_err} máy lỗi script Upload")
     ```
   - Ngưỡng kích hoạt `has_script_alert` bị đặt cứng là `>= 3` máy.
2. **Sai Lệch Quy Mô Thực Tế (Scale Mismatch)**:
   - Trên dàn 80 máy Cụm Kibe (hoặc 160 máy cả Farm), 3 máy lỗi chỉ chiếm **3.75%**.
   - 3 máy lỗi (ví dụ M19 kẹt ATX session, M37 & M42 đen màn hình khi mở app) là các sự cố ngoại cảnh / lag thiết bị cá biệt, không mang tính hệ thống và hoàn toàn không phải "Lỗi script sập hàng loạt".
   - Việc Watchdog tự động đổi tiêu đề tin nhắn thành chuông đỏ `🚨 [FARM ALERT]` gây hoang mang, spam nhóm chat và làm trôi các thông tin điều phối quan trọng.

---

## 3. Quy Chuẩn Ngưỡng Cảnh Báo (Standard Threshold Contract)
1. **Ngưỡng Kích Hoạt Farm Alert Hàng Loạt**:
   - Nâng ngưỡng kích hoạt `has_script_alert` lên **$\ge 8$ máy (tương đương $\ge 10\%$ quy mô cụm farm 80 máy)**.
   - Code chuẩn trong `feed_session_watchdog.py`:
     ```python
     # Bắn Farm Alert khi phát hiện lỗi script hàng loạt (>= 8 máy ~ 10% farm dính lỗi follow hoặc upload)
     has_script_alert = False
     alert_reasons = []
     tot_fl_err = sum(len(b.get("fl_error", [])) for b in cluster_stats) if 'cluster_stats' in locals() else len(fl_error)
     tot_up_err = sum(len(b.get("up_error", [])) for b in cluster_stats) if 'cluster_stats' in locals() else len(up_error) + len(up_timeout)
     if tot_fl_err >= 8:
         has_script_alert = True
         alert_reasons.append(f"{tot_fl_err} máy lỗi script Follow")
     if tot_up_err >= 8:
         has_script_alert = True
         alert_reasons.append(f"{tot_up_err} máy lỗi script Upload")
     ```
2. **Hành Vi Khi Lỗi Dưới Ngưỡng ($< 8$ máy)**:
   - Giữ nguyên tiêu đề báo cáo thông thường: `📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})`.
   - Danh sách máy lỗi (1–7 máy) vẫn được ghi nhận đầy đủ, minh bạch tại dòng `+ Lỗi script/xác minh (N): ...` ở phần chi tiết bên dưới để kỹ thuật theo dõi xử lý, không giật chuông báo động đỏ.

---

## 4. Kiểm Chứng & Đồng Bộ Runtime
- Chạy unit test suite: `pytest python_runner/tests/test_feed_session_watchdog.py -q` (27/27 PASSED).
- Đồng bộ file repo `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` sang runtime cron live `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`.
