# Quy chuẩn Tầng Alert Farm & Triage Phân biệt Quy trình (Nuôi Feed vs Upload Avatar vs Reg/2FA)

## 1. Bản chất sự cố nhầm lẫn Alert (2026-09-03)
- **Hiện tượng:** Khi user đang chạy batch Upload Avatar (`run_tiktok_upload_avatar.ps1` / `Tiktok-video`), máy gặp lỗi hoặc bị dừng ở màn hình Sửa hồ sơ / Thay đổi ảnh, bot lại bắn alert mang template của `tiktok-luot nuoi acc` (`feed_swipe_smoke.py`, `run-feed-session.ps1`) khiến bot và user hiểu nhầm là feed session bị lỗi.
- **Nguyên nhân gốc rễ:**
  1. File `automation-core/src/automation_core/alerts.py` trước đây hardcode fallback `flow_display = flow_file or "feed_swipe_smoke.py"`, `log_display = log_path or ".ai-runs/latest/summary.txt"` và `canary_display = "run-feed-session.ps1"`.
  2. Mẫu alert Telegram thiếu dòng định danh `Quy trình / Script`, chỉ ghi chung chung `[FARM ALERT: MÁY N] DỪNG PHIÊN`.

## 2. Quy chuẩn Tầng Alert trong `automation_core.alerts`
- Mọi alert bắn ra Telegram BẮT BUỘC hiển thị rõ:
  - `• Quy trình / Script: <Tên quy trình>` (Upload Avatar, Nuôi Acc / Lướt Feed, Đăng Video, Follow, Bật 2FA, Đăng Ký TikTok, Đăng Ký Gmail).
  - `• Hiện trường: <Trạng thái hiện trường>`
- `_resolve_script_meta(script_name, machine)` tự động ánh xạ `script_name` sang đúng file flow phụ trách, thư mục log và lệnh canary test tương ứng của từng repo:
  - `tiktok-upload-avatar` / `avatar-upload` ➔ `Tiktok-video/scripts/tiktok_workflow/run_post.py` | `run_tiktok_upload_batch.ps1 -AvatarOnly`
  - `multi-machine-feed-session` / `feed-session-smoke` ➔ `tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py` | `run-feed-session.ps1`
  - `tiktok-video` ➔ `Tiktok-video/scripts/tiktok_workflow/run_post.py` | `run_tiktok_upload_batch.ps1`
  - `tiktok-add-2fa` ➔ `tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py`
  - `Tiktok_Reg` ➔ `Tiktok_Reg/social_reg_v1.py`

## 3. Triage nhanh hiện trường màn hình Sửa hồ sơ / Thay đổi ảnh
- Màn hình bottom-sheet **"Thay đổi ảnh"** (có 2 lựa chọn: *Chụp ảnh*, *Chọn từ Thư viện*, *Hủy*) là của **Upload Avatar**, KHÔNG PHẢI lỗi của lướt feed.
- Khi gặp hiện trường này:
  1. Xác định quy trình đang chạy là Avatar Upload.
  2. Kiểm tra log của `Tiktok-video` / `run_tiktok_upload_avatar.ps1`.
  3. Xử lý selector click "Chọn từ Thư viện" hoặc crop/avatar picker thay vì can thiệp flow nuôi feed.
