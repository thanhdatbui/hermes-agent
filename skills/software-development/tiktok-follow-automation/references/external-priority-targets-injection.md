# External Priority Targets Injection in Follow Runner

## 1. Bản chất & Quy tắc phân vai (Actor vs Target)
- **Workbook / Slot Actor (`taikhoan_run_safe.xlsx`, `tik1..tik8.xlsx`):** CHỈ dành cho tài khoản farm có phiên đăng nhập trên thiết bị thật (Samsung S7). TUYỆT ĐỐI KHÔNG thêm nick ngoài, nick cá nhân hoặc tạo "Row 9" vào workbook vì:
  - App TikTok chỉ hỗ trợ tối đa 8 tài khoản chuyển đổi nhanh.
  - Máy farm không có cookie/password/2FA của nick ngoài -> sẽ fail login / kẹt máy.
- **Priority Target (`config/priority_targets.txt`):** Dành cho nick ngoài cần farm ghé thăm (tương tác view/like/follow chéo). Nick này đóng vai trò là TARGET, không phải ACTOR.

## 2. Cơ chế nạp trong `follow_engine.py`
Trong `FollowEngine.follow_uids()`:
1. Đọc danh sách target từ workbook nội bộ farm (`uid_source_mapping`).
2. Kiểm tra sự tồn tại của file cấu hình priority:
   - Đường dẫn tuyệt đối: `D:/Taadaa/tiktok-follow/config/priority_targets.txt`
   - Hoặc đường dẫn tương đối từ repo root: `config/priority_targets.txt`
3. Parse các UID hợp lệ (bỏ dòng trống, bỏ comment `#`, strip whitespace và `@`).
4. Loại trừ `active_account_handle` (tránh tự follow chính mình).
5. Đẩy các priority UIDs lên ĐẦU danh sách trả về, khử duplicate (`casefold`).

## 3. Quản lý tệp & An toàn phân phối (Drip-feed Safety)
- **File format (`config/priority_targets.txt`):**
  ```text
  # Danh sách nick ngoài cần ưu tiên tương tác
  bangtam2311
  ```
- **State deduplication:** `FollowState` lưu trạng thái đã follow vào SQLite cục bộ theo từng máy/tài khoản. Mỗi nick farm chỉ follow target 1 lần duy nhất, không lặp lại.
- **An toàn thuật toán TikTok:**
  - Không dồn follow hàng loạt cùng thời điểm (tránh bị bot-check/shadowban).
  - Kết hợp lướt feed tự nhiên -> Search UID -> xem video kéo watch-time -> like -> follow.
