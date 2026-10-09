# Triage Nghẽn Pool OmniRoute & Bẫy Báo Cáo "Phantom Success" Trong GPM Login

## 1. Hiện Tượng & Triệu Chứng
- Watchdog báo cáo mỗi ca nạp thành công hàng chục tài khoản (ví dụ `✓ 33`).
- Dòng báo cáo ghi nhận số lượng lớn: `Profile sẵn Google Session chờ OAuth: 97 accounts`.
- **Nhưng thực tế:** Antigravity/Gemini Pool trên OmniRoute (`:20129`) đứng im nhiều ngày không tăng (ví dụ giữ nguyên ở 121 accounts), không có thêm tài khoản mới nào được nạp vào pool.

---

## 2. Các Căn Nguyên Cốt Lõi

### A. Bẫy Báo Cáo "Session Sẵn Chờ OAuth" (Không trừ tài khoản đã nạp)
- **Sai lầm:** Hàm thống kê `_get_gpm_profiles_with_google_session()` quét toàn bộ profile GPM có cookie Google (`SID`, `SSID`, `HSID`, `SAPISID` >= 2) và in ra làm `session_count`.
- **Hệ quả:** Trong 97 profiles có session, thực chất 85 profiles **đã được nạp vào OmniRoute từ trước**. Chỉ có 12 profiles thực sự chưa nạp. Nhãn "chờ OAuth: 97" gây hiểu lầm nghiêm trọng rằng hệ thống đang ứ đọng gần 100 nick chưa xử lý.
- **Quy tắc:** Bắt buộc phải lấy:
  ```python
  pending_oauth_count = len(gpm_with_session - existing_omni_accounts)
  ```

### B. Bẫy "Phantom Success" do Phục Hồi Phiên (Lost Session vs ALREADY_SUCCESS)
- **Cơ chế:** Khi cron nuôi phát hiện nick nghi ngờ mất session $\rightarrow$ ghi cờ `NEEDS_LOGIN` vào `gpm_gmail_nurture_state.json`.
- Watchdog login đọc cờ này và bypass bộ lọc `omniroute_success` để đưa nick vào diện ưu tiên cứu phiên.
- **Điểm nghẽn:** Script thực thi (`run_oauth_s7_pipeline.py`) khi nhận email lại kiểm tra đầu tiên:
  ```python
  if email in status_data.get("omniroute_success", {}):
      return {"status": "ALREADY_SUCCESS"}
  ```
- **Hệ quả:** Script thoát ngay lập tức mà không mở trình duyệt, không đăng nhập lại. Watchdog nhận text `ALREADY_SUCCESS` trong output thì tính là `✓ Thành công`. Toàn bộ 33 lượt thành công trong ca thực chất là 33 lượt skip không làm gì cả, không có session mới và không có OAuth mới.

### C. Bộ Lọc Chặn 100% Của Số Nick Chưa Nạp
Đối với các nick thực sự có session nhưng chưa vào OmniRoute (12 nick), feeder không bốc được vì đều vướng các chốt an toàn:
1. **Cooldown 72h / 7d:** Dính checkpoint hoặc reCAPTCHA trước đó, hệ thống đặt hạn cooldown để hạ nhiệt IP và bảo vệ nick (ví dụ cooldown đến 08/10).
2. **Blacklist / Recovery loại trừ:** Dính email khôi phục bị cấm (như `khoaleemagic`) $\rightarrow$ loại trừ an toàn 100%.
3. **Thiếu Mật Khẩu (No Password):** Tài khoản có profile trong GPM nhưng trong Excel không có cột password $\rightarrow$ feeder không thể lấy mã để exchange OAuth.

---

## 3. Checklist Triage Khi Pool OmniRoute Không Tăng

1. **Kiểm tra tỷ lệ phủ thực tế:**
   - Lấy tập hợp `gpm_with_session` và `existing_omni`.
   - Xác định `unfed_session = gpm_with_session - existing_omni`.
   - Nếu `unfed_session <= 0`: Hệ thống đã bốc cạn toàn bộ tài khoản sẵn có.
2. **Kiểm tra trạng thái của các unfed candidates:**
   - Soi `oauth_pipeline_status.json`: đếm số lượng dính `cooldown_72h`, `cooldown_7days`, `wrong_password_or_checkpoint`, `excluded_khoalee`.
   - Soi `CredentialLookup`: kiểm tra xem các nick này có `password` trong Excel không.
3. **Xử lý Phantom Success trong watchdog:**
   - Phân biệt rõ `NEW_LOGIN_SUCCESS` (đăng nhập thành công profile mới) vs `ALREADY_SUCCESS` (bỏ qua vì đã có trong pool).
   - Tuyệt đối không cộng gộp `ALREADY_SUCCESS` vào chỉ số thành công của ca nạp mới.
