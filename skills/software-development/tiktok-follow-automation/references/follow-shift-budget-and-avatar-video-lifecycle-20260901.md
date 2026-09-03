# Follow Shift Budget, 3-Session Multiplier & Video/Avatar Lifecycle (2026-09-01)

## 1. Cấu Trúc Ca & Budget Follow (1 Ca = 3 Phiên)
- **Cấu trúc ca:** 1 ngày mỗi máy chạy 3 ca, mỗi ca phân cho 1 row (tài khoản):
  - **Ca 1:** Row 1 (ngày lẻ) / Row 2 (ngày chẵn)
  - **Ca 2:** Row 3 (ngày lẻ) / Row 4 (ngày chẵn)
  - **Ca 3:** Row 5 (ngày lẻ) / Row 6 (ngày chẵn)
- **Mỗi ca gồm đúng 3 phiên lướt/follow.**
- **Cấu hình Budget Follow (Chốt 01/09/2026):**
  - `budget_per_session_min: 15`
  - `budget_per_session_max: 20`
  - `budget_per_day: 60`
  - Với 3 phiên/ca, 1 nick chạy đủ ca sẽ follow tích lũy từ 45–60 nick/ngày (đối với nick $\ge 5$ video).
  - Nick $< 5$ video (hoặc Row 3..6 đang trong giai đoạn warmup) tự động khóa `budget = 0` (skip follow hook).

## 2. Quy Trình Upload Video & Đảm Bảo Avatar (Video #1 vs Video #2+)
- **Đăng video lần đầu (Video #1):**
  - Script `run_post.py` / `state_machine.py` tự động kích hoạt `ENSURE_AVATAR`.
  - Tải ảnh từ thư mục nguồn avatar $\rightarrow$ mở *Sửa hồ sơ* $\rightarrow$ crop và lưu avatar $\rightarrow$ hoàn tất flow đăng video.
- **Đăng video các lần tiếp theo (Video #2 trở đi):**
  - Bước `ENSURE_AVATAR` kiểm tra trạng thái avatar trên Profile: nếu đã có (`PRESENT`) $\rightarrow$ ghi nhận `SKIPPED_EXISTING_AVATAR` và thoát ngay, không mở màn hình Sửa hồ sơ hay can thiệp vào avatar.
- **Cơ chế xử lý khi Avatar Fail sau khi Đăng Video Thành Công:**
  - Nếu `POST` và `VERIFY_POST` đã thành công mà `ENSURE_AVATAR` bị lỗi (mất file ảnh, TikTok chặn đổi ảnh, timeout...):
    1. Video **KHÔNG bị đăng lại** (tránh duplicate video).
    2. Workflow chuyển sang `FAILED` / `MANUAL_REVIEW` với `avatar_status: FINAL_BLOCKED`.
    3. Bắn Telegram Farm Alert banner đỏ `[MÁY N] GIỮ HIỆN TRƯỜNG UPLOAD` kèm Device Lock 90m.
    4. Sửa độc lập: Chạy script `run_tiktok_upload_avatar.ps1` với `-AvatarOnly` và `-ForceAvatarMachineList "<máy>"` để up bù avatar mà không đụng đến video hay workbook.
