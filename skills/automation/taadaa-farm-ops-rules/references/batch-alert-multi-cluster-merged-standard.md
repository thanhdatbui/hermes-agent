# Tiêu Chuẩn Gộp Batch Alert Toàn Farm (Kibe + Admin)

**Cập nhật:** 21/09/2026 (User duyệt)

## 1. Bối Cảnh & Mục Tiêu
- Farm gồm 160 máy chia làm 2 cụm:
  * **Cụm Kibe (Local USB):** Máy 1–80, runtime tại `D:/Taadaa/runtime/kibe/live/...`
  * **Cụm Admin (Remote LAN .119):** Máy 201–280, runtime tại `D:/Taadaa/runtime/admin/live/...`
- Khi chạy chung phiên (ví dụ Ca trưa Row 3 12:00), 2 cụm cùng xuất phát và về đích lệch nhau chỉ 1–2 phút.
- **Vấn đề trước đây:** Mỗi cụm chạy hook `batch_aggregator` riêng, bắn 2 tin nhắn cảnh báo rời rạc nhìn y hệt nhau, gây loãng kênh Farm Alerts.
- **Quy chuẩn mới:** BẮT BUỘC gộp làm **1 tin nhắn duy nhất** `【TOÀN FARM】` cho cả 2 cụm.

## 2. Cơ Chế Triển Khai (`automation_core.batch_aggregator`)
1. **Phân loại Cụm (`classify_cluster`):**
   * Nhận diện dải máy: 1..80 -> `kibe`, 201..280 -> `admin`.
   * Nhận diện đường dẫn runtime: bỏ qua thư mục `Users/Kibe`, map theo `runtime/kibe` vs `runtime/admin`.
   * Nhãn chuẩn:
     - `kibe` -> `【FARM KIBE - MÁY 1-80】`
     - `admin` -> `【FARM ADMIN - MÁY 201-280】`
     - `all` -> `【TOÀN FARM】`

2. **Tự động bắt cặp Sibling (`find_sibling_batch_dir`):**
   * Cụm về đích trước tự tìm đường dẫn đối ứng `live/<date>/<window>` của cụm kia.
   * Chờ cụm sau hoàn thành tối đa 120 giây (cấu hình qua env `BATCH_ALERT_MAX_WAIT`).

3. **Cấu trúc tin nhắn gộp (`format_multi_cluster_alert_message`):**
   * **Header toàn farm:**
     `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【TOÀN FARM】`
     • Quy trình / Script: `<tên script>`
     • Quy mô toàn farm: **160 máy** | Thành công: X | Bỏ qua: Y | Thất bại: Z
     • Tổng tỷ lệ thất bại toàn farm: %
   * **Khối riêng từng cụm:**
     * `🏢 【FARM KIBE - MÁY 1-80】`: Chi tiết lỗi vượt ngưỡng, cảnh báo P0 văng account / mất phiên.
     * `🏢 【FARM ADMIN - MÁY 201-280】`: Chi tiết lỗi rớt socket ADB, captcha.
     *(Cụm nào 100% OK sẽ ghi nhận: 100% OK, không có lỗi hệ thống)*
   * **Chỉ dẫn Canary Policy & Recovery:**
     - Nêu máy canary đại diện cho từng cụm gặp lỗi hệ thống (ví dụ: Kibe: M1, Admin: M261).
     - Đính kèm danh sách ảnh hiện trường đại diện.

4. **Chống lặp tin nhắn (Deduplication Marker):**
   * Ghi nhận file marker `.sent` tại `D:/Taadaa/runtime/cron-state/batch-alerts/<session_key>.sent`.
   * Cụm về sau kiểm tra thấy marker đã tồn tại -> **Silent Skip**, không gửi thêm tin thứ 2.
