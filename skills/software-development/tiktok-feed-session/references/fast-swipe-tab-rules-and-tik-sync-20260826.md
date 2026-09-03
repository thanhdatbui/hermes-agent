# Quy tắc Tương tác Fast Swipe, Phân tách Tab và Cơ chế Đồng bộ Tik Workbooks (2026-08-26)

## 1. Cơ chế Bù Tỉ lệ Tương tác cho Fast Swipe (Deep Inspect Boost)
- **Vấn đề cốt lõi:** Khi áp dụng cơ chế Fast Swipe (2–4 video lướt nhanh mù 2.0s–5.0s không dump XML $\rightarrow$ mới có 1 video Deep Inspect dump XML), các video lướt nhanh không thể tương tác Like/Follow. Nếu giữ tỉ lệ Like (8%) và Follow (5%) per-video thông thường, số lượng tương tác trong cả phiên 8–12 video sẽ bị loãng xuống gần như bằng 0.
- **Quy tắc Bù Tỉ lệ tại nhịp Deep Inspect:**
  - `deep_like_rate_percent`: Nâng lên **40%** tại nhịp Deep Inspect.
  - `deep_follow_rate_percent`: Thiết lập **20%** tại nhịp Deep Inspect.
  - Khi operator không cấu hình `like_rate` / `follow_rate` tường minh, hệ thống tự động áp dụng `deep_like_rate_percent` và `deep_follow_rate_percent` tại các video Deep Inspect để đảm bảo phiên nuôi đạt trung bình 1–2 Like và 1–2 Follow organic tự nhiên.

## 2. Quy tắc Phân tách Tab cho Fast Swipe
- **Tab Đề xuất (For You / FYP - 85% thời lượng):**
  - Áp dụng Fast Swipe xen kẽ Deep Inspect (2–4 video lướt nhanh $\rightarrow$ 1 video Deep Inspect).
  - Video đầu tiên (baseline) và video cuối cùng của phiên bắt buộc phải là Deep Inspect.
- **Tab Đang theo dõi (Following - 8% thời lượng) & Tab Bạn bè (Friends - 7% thời lượng):**
  - **TUYỆT ĐỐI KHÔNG ÁP DỤNG FAST SWIPE.**
  - Khi chuyển sang tab Following hoặc Friends, **100% video bắt buộc phải Deep Inspect (dump XML)** để đọc UI, nhận diện tài khoản quen/bạn bè và tương tác Like (Following 15%, Friends 25%) chuẩn xác theo đúng tỉ lệ ưu tiên.

## 3. Kiến trúc Đồng bộ 1 Chiều Master sang Tik Workbooks
- Master root: `taikhoan_dat_v2_updated .xlsx` (8 slot/máy).
- Đích đồng bộ: `Tik1.xlsx` (Slot 1), `Tik2.xlsx` (Slot 2), `tik3.xlsx` (Slot 3), `Tik4.xlsx` (Slot 4).
- Công thức ánh xạ: $\text{Folder} = (\text{Machine} - 1) \times 8 + \text{Slot}$.
- **Invariant bảo toàn:**
  - Chỉ cập nhật/ghi đè cột `Tên Tài Khoản` (ID) khi ID mới là username TikTok hợp lệ (regex `^[a-zA-Z0-9_.]{2,24}$`) hoặc dọn sạch placeholder rác (`http://`, `ghjfghj`, `none`, `null`).
  - **TUYỆT ĐỐI KHÔNG LÀM THAY ĐỔI CỘT `Folder Video` VÀ `Video Đã Đăng`** (không bao giờ reset về 0).
- **Giao dịch All-or-Nothing có Journal Rollback:**
  - Tạo snapshot backup trước khi ghi bất kỳ file Tik nào.
  - Nếu xảy ra lỗi ghi hoặc crash giữa chừng, toàn bộ các file đã sửa đổi trước đó sẽ được tự động rollback về snapshot ban đầu để chống rách nát dữ liệu liên workbook.
