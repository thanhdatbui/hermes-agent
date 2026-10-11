# Lifecycle Supervisor Fail-Closed BLOCKED Handling & Triage

## 1. Cơ Chế Fail-Closed Gán Trạng Thái BLOCKED
Trong `batch_gpm_5profiles_supervisor.py`:
- Khi bất kỳ tài khoản nào thực thi stage (đặc biệt là `CHANGE_INFO` hoặc `CHATGPT_REG`) trả về kết quả `FAILED` hoặc `ERROR`:
  ```python
  if res_status in {"FAILED", "ERROR"}:
      if result.get("stage") == "HOTMAIL_LOGIN" and int(info.get("login_retry_count") or 0) >= 3:
          info["status"] = "QUARANTINE"
      else:
          info["status"] = "BLOCKED"
  ```
- Trạng thái `BLOCKED` là cơ chế **bảo vệ chủ động (fail-closed)**:
  - Ngăn chặn vòng lặp retry vô tận làm Microsoft khóa/checkpoint tài khoản.
  - Bảo vệ proxy IP di động không bị burn/blacklist do liên tục gửi request lỗi.
  - Giải phóng hàng đợi: hàm `select_candidates()` chủ động bỏ qua các tài khoản `status in {"FAILED", "ERROR", "BLOCKED", "QUARANTINE"}` để ưu tiên chạy các tài khoản đủ điều kiện khác.

## 2. Các Nguyên Nhân Phổ Biến Dẫn Đến BLOCKED Ở CHANGE_INFO
1. **Cooldown IP 24h (`IP_COOLDOWN_BLOCKED`):**
   - Proxy di động của máy đó vừa thực hiện đổi thông tin cho 1 tài khoản khác trong vòng 24 giờ trước.
   - Script tuân thủ nghiêm ngặt quy tắc 1 IP/ngày để tránh Microsoft phát hiện hành vi đổi pass hàng loạt.
2. **Microsoft Rate Limit Gửi Mã OTP:**
   - Khi Microsoft yêu cầu xác minh danh tính qua email khôi phục chính chủ (`thanhdatbui1995@gmail.com`) nhưng chạm giới hạn trong ngày (*"Bạn đã yêu cầu quá nhiều mã trong ngày hôm nay"*).
   - Cần chờ sang ngày mới (hết chu kỳ 24h) để hạn mức gửi OTP được reset.
3. **Lỗi Giao Diện / Popup Microsoft:**
   - Microsoft hiển thị giao diện mới chưa load kịp selector `#proof-confirmation-email-input`, `#codeEntry-0`, hoặc bị timeout khi bung form `#iPlainTextData` lấy TOTP secret key.
4. **Thiếu Dữ Liệu Khôi Phục (Missing Recovery Email / Secret):**
   - Tài khoản chưa được map email khôi phục hoặc secret key 2FA trong bảng tính.

## 3. Quy Trình Triage & Mở Khóa Cuốn Chiếu
- **Không vội reset đồng loạt:** Tuyệt đối không chuyển toàn bộ BLOCKED về PENDING cùng một lúc vì sẽ gây nghẽn proxy và dính lại IP cooldown.
- **Phân loại theo nguyên nhân:**
  1. Kiểm tra mtime và last run trong `hotmail_changed_tracker.json` (`ip_cooldowns` và `cooldown_emails`).
  2. Với các tài khoản do IP cooldown: chờ đủ 24h, IP cooldown hết hạn thì mở khóa từng batch nhỏ (1-2 tài khoản/máy).
  3. Với các tài khoản do chạm OTP limit: chờ sang ngày hôm sau để Microsoft reset hạn mức.
  4. Với các tài khoản thiếu recovery info: rà soát đối soát lại Excel nguồn trước khi mở khóa.

## 4. Kỷ Luật Phản Hồi Khi Nhận Cronjob Lifecycle Report
- Khi báo cáo 6H (`hotmail-gpm-lifecycle-6h-report`) được tự động inject vào session qua cơ chế cron delivery:
  - **CẤM lặp lại vô nghĩa:** Không viết đoạn văn dài chỉ để diễn giải/chép lại các con số đã hiển thị rõ ràng trên báo cáo.
  - **Tập trung vào delta & hành động:** Chỉ nêu bật các biến động quan trọng (số lượng DONE mới tăng, số lượng BLOCKED mới phát sinh) và phân loại ngắn gọn nguyên nhân nếu có sự cố cần can thiệp.
