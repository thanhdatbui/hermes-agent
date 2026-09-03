# Bù Tỉ Lệ Tương Tác (Like/Follow) Trong Cơ Chế Fast Swipe & Đồng Bộ Tik Workbooks (2026-08-26)

## 1. Cơ Chế Bù Tỉ Lệ Tương Tác Tại Nhịp Deep Inspect (Dump XML)

### Bối cảnh & Vấn đề:
- Hệ thống áp dụng cơ chế **Fast Swipe (2–4 video lướt nhanh mù 2.0–5.0s không dump XML)** xen kẽ **1 video Deep Inspect (có dump XML đầy đủ)** để giảm tải RAM cho Samsung S7.
- Nếu chỉ giữ tỉ lệ Like (8%) và Follow (5%) thông thường trên mỗi video, thì trong các nhịp Fast Swipe bot hoàn toàn không thể tương tác. Hệ quả là trên cả phiên (8–12 video), xác suất like/follow bị loãng xuống cực thấp (gần như 0).

### Giải pháp kỹ thuật:
- **Nâng Like Rate tại Deep Inspect (`DEFAULT_DEEP_LIKE_RATE_PERCENT`):** Tăng từ `20%` lên **`40%`**.
- **Thêm Follow Rate tại Deep Inspect (`DEFAULT_DEEP_FOLLOW_RATE_PERCENT`):** Đặt **`20%`** tại nhịp dump XML.
- Khi không có cấu hình override tường minh (`_like_rate` / `_follow_rate`), luồng `feed_swipe_smoke.py` tự động áp dụng `deep_like_rate_percent` và `deep_follow_rate_percent` tại các nhịp Deep Inspect để bù đắp cho các video lướt nhanh trước đó, đảm bảo 1 phiên lướt vẫn có 1–2 like và 1 follow organic tự nhiên.

---

## 2. Đồng Bộ 1-Chiều ID Tài Khoản Sang Tik Workbooks (`sync-tik-workbooks.py`)

### Quy tắc Mapping & Invariant:
- Master Root: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (8 slots/máy).
- Slot Mapping:
  * Slot 1 $\rightarrow$ `Tik1.xlsx` (Ca 1 / Sáng)
  * Slot 2 $\rightarrow$ `Tik2.xlsx` (Ca 2 / Chiều)
  * Slot 3 $\rightarrow$ `tik3.xlsx` (Ca 3 / Tối)
  * Slot 4 $\rightarrow$ `Tik4.xlsx` (Ca 4 / Dự phòng)
  * Công thức chuẩn: $\text{Slot} = \text{Folder} - ((\text{Máy} - 1) \times 8)$.

### Nguyên tắc bảo toàn:
- **Bảo toàn cột `Folder Video` và `Video Đã Đăng`:** Quá trình sync CHỈ cập nhật cột `Tên Tài Khoản` (ID) khi ID mới là username hợp lệ (regex `^[a-zA-Z0-9_.]{2,24}$`) hoặc xóa trắng khi ô hiện tại mang chuỗi rác (`http://`, `ghjfghj`, `none`, `null`).
- **Giao dịch All-or-Nothing có Journal Snapshot:** Tự động sao lưu snapshot trước khi ghi. Nếu có bất kỳ lỗi nào xảy ra trong quá trình cập nhật liên file, hệ thống tự động rollback toàn bộ các workbook về trạng thái ban đầu.
- **Không xung đột với `taikhoan_run_safe.xlsx`:** Master phân phối độc lập 1 chiều sang file feed và các file upload, không ghi đè chéo.
