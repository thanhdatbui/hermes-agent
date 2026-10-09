# Quy Chuẩn Bắn Farm Alert Khi Lỗi Script Hàng Loạt & Báo Cáo Định Danh Theo Username

## 1. Bắt Buộc Bắn Farm Alert Khi Lỗi Script Hàng Loạt (Cả Follow Lẫn Upload)
- **Quy tắc bất biến (User Directive Invariant):**
  *"Tóm lại lỗi script hàng loạt thì phải bắn về farm alert kể cả script follow hay upload video"*.
- **Lỗ hổng cũ đã giải quyết:**
  `batch_aggregator.py` trước đây chỉ đọc `final_status` của bước lướt feed trong `run_manifest.json`, hoàn toàn bỏ qua `follow_result.json` và `upload_result.json`. Khi hàng loạt máy lướt feed thành công nhưng kẹt mở tab follow hoặc timeout upload, hệ thống vẫn coi ca chạy là 100% OK và không phát cảnh báo.

### Cơ Chế 2 Tầng Bắt Buộc:
1. **Tầng 1: Batch Alert Tức Thời (`automation-core/src/automation_core/batch_aggregator.py`):**
   - Đọc trực tiếp `follow_result.json` và `upload_result.json` trong `artifact_root` của từng máy.
   - Phân loại lỗi chuẩn hóa: `FollowScriptError` (MANUAL_REVIEW, exception, fail), `FollowReleasedError` (FOLLOW_FAILED), `UploadScriptError` (timeout, error, fail). Bỏ qua các trường hợp skip hợp lệ (dưỡng sinh, chưa đủ video, đã upload trong ca...).
   - **Ngưỡng kép kích hoạt:** Khi $\ge 3$ máy (hoặc $\ge 10\%$ số máy) gặp cùng signature lỗi $\rightarrow$ Kích hoạt ngay:
     `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI SCRIPT LAN RỘNG`
     kèm danh sách máy lỗi và chỉ dẫn máy Canary để test.
2. **Tầng 2: Farm Alert Trong Báo Cáo Ca Nuôi (`feed_session_watchdog.py`):**
   - Đồng bộ ở cả bản live cron (`C:/Users/Kibe/AppData/Local/hermes/scripts/`) và repo Git (`D:/Taadaa/tiktok-luot nuoi acc/scripts/`).
   - Khi phát hiện $\ge 3$ máy lỗi script Follow hoặc Upload trong ca:
     * Tiêu đề tự động đổi thành: `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (X máy lỗi script Follow/Upload) - Ca X (Row Y)`.
     * Gom nhóm chi tiết lỗi theo nguyên nhân (ví dụ: `Kẹt mở tab Đã follow (3: M32, M43, M45)`). Triệt tiêu việc chỉ in số máy cộc lốc `32, 43, 45`.

---

## 2. Quy Chuẩn Báo Cáo Định Danh Theo Tài Khoản / Username (@username)
- **Quy tắc bảo vệ:**
  Mọi báo cáo đối soát, kiểm tra nhả follow hoặc thống kê tăng trưởng BẮT BUỘC phải quy về **TÊN NICK / USERNAME CỤ THỂ (@username)** (kèm số máy/Row phụ trợ).
- **Cấm tuyệt đối:**
  Chỉ báo cáo mỗi "số máy" chung chung, vì mỗi máy chạy nhiều nick qua các Row khác nhau (chủ yếu Row 1 và Row 2). Người vận hành cần kiểm chứng dữ liệu thật trên từng tài sản nick TikTok cụ thể.
