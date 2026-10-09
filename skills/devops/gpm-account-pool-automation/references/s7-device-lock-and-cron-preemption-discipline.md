# Samsung S7 Device Lock Preemption & Anti-Interactive Probing Discipline

## 1. Bối Cảnh Hiện Trường & Nguyên Nhân Gốc Rễ (2026-09-05)

Khi thực hiện đăng nhập Gmail lên profile GPMLogin và gặp thử thách bảo mật của Google đòi xác nhận trên Samsung Galaxy S7 (Google Prompt `challenge/dp` hoặc Security Code `challenge/ootp`):
- **Hiện tượng lỗi:** Subagent worker bị sa lầy 80-110+ turns, liên tục chạy các lệnh ad-hoc `python -c` trong terminal để gửi `input swipe`, `input tap`, đọc XML UI dump nhưng vẫn bị kẹt ở màn hình Launcher / Home Screen hoặc thư mục ứng dụng.
- **Nguyên nhân cốt lõi (User Invariant):**
  - Worker **KHÔNG gọi `acquire_device_lock`**.
  - Trong lúc đó, các tiến trình cron nuôi tài khoản định kỳ của Farm (`python_runner/run_tiktok.py` / GemPhone) đang chạy nền trên chính chiếc điện thoại đó.
  - Mỗi khi worker bật Google Settings (`GoogleSettingsLink`) hoặc mở notification lên thì cron TikTok lập tức chiếm lại foreground, swipe màn hình hoặc đưa máy về TikTok/Launcher.
  - Worker lầm tưởng là tap trượt tọa độ và tiếp tục lặp lại các lệnh probe thủ công trong vô vọng.

---

## 2. Nguyên Tắc Bắt Buộc: CẤM BẤM TAY MÒ MẪM & BẮT BUỘC DEVICE LOCK

### A. CẤM TUYỆT ĐỐI Subagent "Mò Bấm Tay" Rời Rạc
- CẤM subagent chạy các lệnh `python -c` hay shell đơn lẻ để tap/swipe dò dẫm từng pixel trên thiết bị Farm.
- MỌI thao tác điều khiển thiết bị S7 BẮT BUỘC phải được đóng gói thành **hàm Python hoàn chỉnh trong file script vật lý** (như hàm `get_s7_security_code` trong `D:\Taadaa\GPM auto\scripts\run_batch_login_6machines.py`).

### B. Bắt Buộc Khóa Thiết Bị Với `force_preempt=True`
Mọi tương tác ADB vào máy S7 để lấy mã hoặc duyệt prompt BẮT BUỘC phải bọc trong context manager:

```python
from automation_core.device_lock import acquire_device_lock

with acquire_device_lock(
    machine=str(machine_id),
    serial=serial,
    project="gpm-login",
    bypass_proxy_readiness=True,
    force_preempt=True
):
    # 1. Bật màn hình, mở Google Settings / Security Code
    # 2. Lấy mã 10 số (hoặc tap Yes duyệt Prompt)
    # 3. Luôn nhấn keyevent 3 (HOME) trước khi nhả lock
    subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "3"], timeout=5)
```

- **`force_preempt=True`**: Tạm dừng và đình chỉ ngay quyền chiếm màn hình của các cron TikTok / GemPhone đang chạy, bảo đảm S7 ở trạng thái cô lập 100% trong 1-2 phút lấy mã.
- **Dọn dẹp sau khi lấy mã:** Bắt buộc bấm phím HOME (`input keyevent 3`) để đưa điện thoại về trạng thái sạch trước khi thoát context manager nhả lock, tránh để màn hình Cài đặt làm gián đoạn ca chạy TikTok tiếp theo.

---

## 3. Thứ Tự Ưu Tiên Vượt Thử Thách Đăng Nhập (Two-Tier Hierarchy)

Không phải lúc nào cũng cần đụng vào điện thoại S7. Khi Google đưa ra thử thách xác minh danh tính, tuân thủ đúng thứ tự 2 tầng:

### Tầng 1: Ưu Tiên Số 1 — IMAP Recovery Email OTP (Hoàn toàn trên Web)
- Khi gặp màn hình `challenge/selection`, kiểm tra xem có dòng chọn email khôi phục (`thanhdatbui1995@gmail.com`) hay không.
- Nếu có: Click chọn gửi mã về email khôi phục $\rightarrow$ Dùng module IMAP `fetch_latest_otp` từ `D:\Taadaa\add mail khoi phuc\read_otp_mail.py` (với app password trong Windows Env `OTP_MAIL_APP_PASSWORD`) để lấy mã 6 số điền vào trình duyệt.
- **Ưu điểm:** Nhanh (~5-10s), 100% tự động trên trình duyệt, không cần chạm tới ADB hay màn hình điện thoại S7.

### Tầng 2: Dự Phòng — S7 Security Code Bọc Trong Device Lock
- Nếu Google không cho chọn email khôi phục mà bắt buộc nhập mã Offline OTP 10 số (`challenge/ootp`) hoặc Google Prompt (`challenge/dp`):
  1. Gọi `acquire_device_lock(machine=..., serial=..., force_preempt=True)`.
  2. Forward port ATX-Agent: `adb -s <serial> forward tcp:<17000+m> tcp:7912`.
  3. Mở intent trực tiếp: `com.google.android.gms/.app.settings.GoogleSettingsLink`.
  4. Trích xuất mã bảo mật 10 số (regex `^\d{10}$`) $\rightarrow$ Điền vào ô input trên Chrome.
  5. Bấm `keyevent 3` (HOME) và nhả lock.

---

## 4. Tách Vĩnh Viễn Khỏi S7 Ngay Sau Khi Đăng Nhập Thành Công
- Ngay sau khi vượt qua thử thách đăng nhập, **BẮT BUỘC MỞ NGAY**:
  `https://myaccount.google.com/two-step-verification/authenticator`
- Kích hoạt Google Authenticator (TOTP), trích xuất Secret Key Base32 (32 ký tự) và lưu đồng bộ vào:
  - `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`
  - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`
- **Kết quả:** Từ lần đăng nhập sau trên PC, script chỉ cần bấm *"Thử cách khác"* $\rightarrow$ *"Ứng dụng Authenticator"* $\rightarrow$ điền mã TOTP 6 số từ Excel, **vĩnh viễn không bao giờ cần đụng tới máy S7 nữa**.

---

## 5. Quy Tắc Proxy Pairing & Phân Phối Batch An Toàn
- Toàn bộ 80 máy Kibe map với **40 proxy vật lý** (2 máy/proxy):
  - 32 cổng Mobi 4G (`5101..5108`, `5111..5118`, `5121..5128`, `5131..5138`).
  - 7 cổng MikroTik (`10001..10007`).
  - 1 cổng Khoalee (`16002`).
- **Nguyên tắc an toàn:**
  - CẤM login nhiều Gmail trên cùng 1 cổng proxy trong cùng một batch (tránh Google nghi vấn spam mạng và bắt checkpoint SMS `challenge/iap`).
  - Mỗi proxy chỉ chạy tối đa 1 tài khoản mỗi phiên. Nếu cần chạy tài khoản của máy cặp, bắt buộc giãn cách tối thiểu 2-3 tiếng.
  - Cài đặt Circuit Breaker: Nếu gặp $\ge 2$ tài khoản lỗi liên tiếp, dừng batch khẩn cấp, đóng sạch profile và báo cáo.
