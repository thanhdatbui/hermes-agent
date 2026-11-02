# SQLite Master Ledger, DB Browser & Web Dashboard Access (2026-11-02)

## 1. Phương Thức Truy Cập Dữ Liệu SQLite Chuẩn Farm
- **Single Source of Truth (SSOT):** `D:/Taadaa/data/farm_master.db` (các bảng `orders`, `machines`, `tiktok_accounts`, `mailboxes`, `slot_assignments`).
- **Giao diện Web Dashboard:** `http://localhost:1905` (hoặc `http://192.168.110.2:1905` qua LAN).
  - Tích hợp endpoint `/api/orders` hiển thị đầy đủ danh sách đơn, timeline bưu cục và ảnh chụp màn hình bóc tách từ máy farm.
  - Phục vụ xem nhanh, không bao giờ bị lock file hay phân mảnh như Excel.
- **Desktop GUI Viewer (Cài sẵn trên máy):**
  - Phần mềm: `DB Browser for SQLite` tại `C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe`.
  - Mở trực tiếp: `cmd.exe /c start "" "C:\Program Files\DB Browser for SQLite\DB Browser for SQLite.exe" "D:\Taadaa\data\farm_master.db"`.
  - Duyệt dạng bảng lưới (grid) tại tab `Browse Data` -> chọn table `orders`.

## 2. Kỷ Luật Tool-Use Enforcement & Chống Hứa Hẹn Suông
- **Bẫy cam kết thụ động:** Coordinator tuyệt đối không được dùng câu thoại hứa hẹn "anh chỉ cần bảo, em sẽ bật..." mà không gọi tool, vì sẽ vi phạm trực tiếp cơ chế Tool-Use Enforcement.
- **Hành động ngay:** Khi người dùng hỏi về công cụ xem hoặc yêu cầu kiểm tra dữ liệu, Coordinator BẮT BUỘC khởi chạy ngay công cụ (hoặc gọi tool kiểm tra tiến trình `tasklist` / HTTP status) trong cùng lượt phản hồi và cung cấp bằng chứng hoàn tất.
