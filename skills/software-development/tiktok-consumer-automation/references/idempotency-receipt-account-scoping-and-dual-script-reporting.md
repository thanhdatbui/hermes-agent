# Idempotency Post Receipt Scoping & Dual-Script Reporting

## 1. Idempotency Receipt Scoping Theo Tài Khoản (`Tiktok-video`)
- Khi một thiết bị chạy nhiều tài khoản khác nhau qua các ca (Tik1, Tik2, Tik3, Tik4):
  + Mỗi tài khoản đều bắt đầu đăng từ Video 1..N.
  + File receipt chống đăng trùng (`post-attempts`) **bắt buộc** phải gắn định danh theo tài khoản:
    `machine_{machine}_account_{safe_account}_video_{video_number}.json`.
  + Hàm `_load_post_attempt_receipt` và các hàm quét completed/pending receipts phải kiểm tra trường `target_account`. Nếu receipt thuộc nick cũ, phải bỏ qua, cấm để receipt nick cũ chặn nút `Đăng` của nick mới.

## 2. Báo Cáo Tách Bạch Cả 2 Script (Feed vs Upload)
- Khi nuôi acc kết hợp hook đăng video ở Phiên 3:
  + Cấm báo cáo thành công gộp chung nếu Feed thành công mà Upload thất bại.
  + Luôn tách bạch rõ ràng 2 công đoạn trong watchdog / summary / báo cáo user: `Lướt Feed (Success/Fail)` và `Đăng Video (Success/Fail kèm lý do/Skipped)`.
  + Kiểm chứng canary bắt buộc đối soát `upload_result.json`, `report.json`, grid profile và workbook.
