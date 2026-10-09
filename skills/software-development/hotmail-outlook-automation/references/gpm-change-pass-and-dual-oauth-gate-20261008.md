# GPM Hotmail Change Pass & Dual-OAuth Eligibility Gate Invariant (2026-10-08)

## 1. KHAI TỬ LUỒNG ĐỔI PASS TRÊN ĐIỆN THOẠI S7 & 100% CHUYỂN SANG GPM
- **Khai Tử Toàn Bộ Cron S7:** Đã gỡ bỏ vĩnh viễn toàn bộ cronjob đổi pass Hotmail qua ADB Chrome trên điện thoại Samsung S7:
  - `night-hotmail-security-watchdog` (Job ID: `32d81babe28e`) -> ĐÃ XÓA.
  - `m30-hotmail-retry-watchdog` (Job ID: `80ffdc1d949b`) -> ĐÃ XÓA.
- **CẤM TUYỆT ĐỐI** tạo lại hoặc sử dụng điện thoại S7 để lướt web Microsoft đổi mật khẩu Hotmail. Điện thoại S7 chỉ phục vụ nuôi TikTok farm và nhận mail qua Outlook app nếu cần. Việc đổi pass trên mobile gây ra:
  - Lỗi font và giao diện web mobile co cụm, khó kiểm soát selector.
  - Xung đột DeviceLock với các ca nuôi TikTok feed / dọn cache.
  - IP mobile 4G proxy bị Microsoft nghi ngờ gây checkpoint dày đặc.
- **100% QUA GPM:** Toàn bộ quy trình đổi mật khẩu Hotmail, gỡ mail khôi phục shop và Sign out everywhere BẮT BUỘC thực hiện qua **GPMLogin Profiles** bằng Playwright / CDP (`D:\Taadaa\Hotmail\scripts\gpm_change_hotmail_security.py` hoặc qua Supervisor `D:\Taadaa\GPM auto\scripts\batch_gpm_5profiles_supervisor.py`).

## 2. ĐIỀU KIỆN ĐỦ ĐỂ CHANGE PASS (DUAL-OAUTH ELIGIBILITY GATE)
Tài khoản Hotmail **CHỈ ĐỦ ĐIỀU KIỆN CHANGE PASS** khi thỏa mãn đồng thời cả 3 tiêu chí:
1. **Đã đăng ký thành công Codex:** Đã qua 5SIM / ChatGPT, có credentials Codex hoạt động.
2. **Đã nạp OAuth vào OmniRoute (:20129):**
   - Database: `C:\Users\Kibe\.omniroute\storage.sqlite`
   - Bảng: `provider_connections`
   - Điều kiện: `provider = 'codex' AND LOWER(email) = LOWER(?) AND is_active = 1`
3. **Đã nạp OAuth vào 9Router (:20128):**
   - Database: `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`
   - Bảng: `providerConnections`
   - Điều kiện: `provider = 'codex' AND LOWER(email) = LOWER(?) AND isActive = 1`

**Nguyên tắc Fail-Closed:**
- Nếu tài khoản thiếu OAuth ở bất kỳ server nào trong 2 server trên: **CẤM TUYỆT ĐỐI chuyển sang stage `CHANGE_INFO`**.
- Giữ nguyên tài khoản ở trạng thái chờ (`WAITING_DUAL_OAUTH` hoặc tiếp tục ngâm), tuyệt đối không được đổi pass vì đổi pass sẽ làm đứt phiên đăng nhập trước khi kịp khai thác quota Codex cho cả 2 proxy LLM.

## 3. TIÊU CHUẨN BÁO CÁO TIẾN ĐỘ CHANGE PASS ĐẦY ĐỦ (REPORTING METRICS)
Báo cáo định kỳ (6h) hoặc báo cáo theo yêu cầu của User BẮT BUỘC phải thể hiện các chỉ số rõ ràng, minh bạch:
- **Tổng số Hotmail trong Queue:** Số lượng tài khoản Hotmail đang theo dõi.
- **Codex OmniRoute (:20129):** Số lượng tài khoản đã có OAuth trên OmniRoute.
- **Codex 9Router (:20128):** Số lượng tài khoản đã có OAuth trên 9Router.
- **Đủ điều kiện Change Pass (Dual-Eligible):** Số lượng tài khoản có mặt trên CẢ 2 proxy server.
- **Đang ngâm 7 ngày (`WAIT_7D`):** Số lượng tài khoản đang trong thời gian ngâm an toàn.
- **Đang chờ đổi pass (`CHANGE_INFO`):** Số lượng tài khoản thỏa mãn tất cả điều kiện, đang chờ GPM xử lý.
- **Đã hoàn thành (`DONE`):** Số lượng tài khoản đã đổi pass mới + gỡ mail khôi phục shop + sign out everywhere thành công và đã cập nhật Master Excel.
- **Thất bại / Quarantine:** Danh sách tài khoản gặp sự cố (sai pass ban đầu, checkpoint, block IP) để kịp thời xử lý.
