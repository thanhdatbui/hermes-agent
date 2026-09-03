# Quy tắc Báo Cáo Tách Bạch 2 Script & Idempotency Scoping Theo Tài Khoản

## 1. Quy tắc Báo Cáo Tách Bạch (Feed vs Upload)
Khi chạy flow tích hợp nuôi acc (Feed Session) kết hợp hook Đăng Video (Upload Hook ở Phiên 3):
- **CẤM** kết luận phiên hoàn tất thành công chung khi chỉ có Feed chạy xong mà Upload Hook thất bại hoặc chưa chạy.
- Báo cáo (Telegram Watchdog, log tổng kết, và báo cáo cho user) **bắt buộc** phải phân tách rõ ràng 2 công đoạn:
  + **Lướt Feed**: `Success (N): M1, M2... | Fail (M): M3...`
  + **Đăng Video (Phiên 3)**: `Success (N): M1, M2... | Fail (M): M3(lý do)... | Bỏ qua (K): ...`
- Nếu Lướt Feed thành công nhưng Upload thất bại, phải báo rõ `Lướt: SUCCESS | Upload: FAILED (lý do cụ thể)`.

## 2. Quy tắc Đối Soát Evidence Khi Kiểm Chứng Live Canary
- Khi chạy live canary trên máy thật để nghiệm thu tính năng/sửa lỗi:
  + Không chỉ dừng lại ở việc kiểm tra log swipes của feed-session.
  + Bắt buộc phải đọc và đối soát file `upload_result.json` và `report.json` của runner upload.
  + Kiểm tra trạng thái thực tế trên UI thiết bị: Video đã xuất hiện trên lưới trang cá nhân (Profile Grid) chưa, workbook Tik tương ứng đã cập nhật `Video Đã Đăng` chưa.
  + Tuyệt đối không xóa lock thiết bị và báo pass khi upload hook trả về `failed` hoặc exit code khác 0.

## 3. Idempotency Receipt Scoping Theo Tài Khoản (`Tiktok-video`)
- Trên hệ thống farm 1 máy chạy nhiều tài khoản (3-4 ca / 3-4 row workbook: Tik1, Tik2, Tik3, Tik4):
  + Mỗi tài khoản đều bắt đầu đăng từ Video 1..N.
  + File receipt chống đăng trùng (`post-attempts`) **bắt buộc** phải được định danh kèm theo tên tài khoản:
    `machine_{machine}_account_{safe_account}_video_{video_number}.json`.
  + Khi đọc các file receipt cũ (legacy `machine_{machine}_video_{video_number}.json`), **phải kiểm tra trường `target_account`** bên trong JSON. Nếu receipt thuộc về tài khoản khác (ví dụ nick cũ từ ca khác/ngày trước), phải bỏ qua, không được để receipt cũ chặn tài khoản mới bấm nút `Đăng`.
