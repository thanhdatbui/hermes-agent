# Feed Profile Mismatch & Auto-Login Recovery Invariant

## 1. Bản Chất Sự Cố & Chỉ Thị Cốt Lõi Từ User
- **Hiện tượng báo động:** Watchdog báo lỗi `Lệch Profile/Nick TikTok` (ví dụ M261, M274) do Profile username hiện tại không khớp nick mục tiêu hoặc không tìm thấy nick trong Switcher.
- **User steering invariant:** "Tại sao lại k tự login tiktok đúng nick trong ca chạy".
- **Quy tắc tuyệt đối:** Cứ phát hiện nick không đúng hoặc thiếu account (`ACCOUNT_MISSING`, `profile account mismatch`), hệ thống BẮT BUỘC phải tự động phục hồi thay vì dừng máy fail-closed.

## 2. Quy Trình Auto-Recovery 2 Bước Cho Feed Runner
Khi Feed Runner kiểm tra Profile hiện tại trước khi bắt đầu lướt feed:
1. **Bước 1 — Auto-Switch trong Switcher:**
   - Mở modal Switch Account (`Account Switcher`).
   - Quét danh sách account đang đăng nhập trên thiết bị.
   - Nếu thấy nick mục tiêu: Tap chọn để switch sang nick đúng và tiếp tục ca nuôi feed bình thường.
2. **Bước 2 — Auto-Login / Reconcile Khi Thiếu Slot:**
   - Nếu nick mục tiêu hoàn toàn không có trong Switcher:
     + Không abort fail-closed nhả máy.
     + Kích hoạt lệnh nạp bù / reconcile tự động:
       ```bash
       python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py \
           --workbook "<cluster_taikhoan_run_safe_xlsx>" \
           --machines <machine_id> \
           --expected-username <target_username> \
           --login-project "D:/Taadaa/Tiktok_Reg" \
           --allow-live-reconcile
       ```
       hoặc gọi handler login trực tiếp: `tiktok_login_v1.py <machine_id> --all --allow-parent-lock`.
     + Sau khi login thành công, chuyển sang nick mới nạp và tiếp tục phiên nuôi feed.

## 3. Đồng Bộ Trạng Thái Với Watchdog
- Trạng thái `Lệch Profile/Nick TikTok` (`profile account mismatch`) trong `watchdog.formatters.classify_feed_failure` chỉ được phép ghi nhận nếu cả 2 bước Auto-Switch và Auto-Login Recovery đều thất bại sau khi đã thử tự động.
- CẤM phân biệt giữa ca Đăng video (Upload Hook) và ca Nuôi feed (Feed Nurture): cả hai luồng đều phải tuân thủ chuẩn tự động nạp bù nick khi Switcher thiếu tài khoản mục tiêu.
