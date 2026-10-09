# Kỷ Luật Tích Hợp IMAP Recovery OTP & Preemptive S7 Security Code

## 1. Bối cảnh & Nguyên tắc Cốt lõi
Khi tự động hóa đăng nhập Google trên GPM cho dàn tài khoản Kibe Farm S7:
- **Cấm kỵ:** CẤM TUYỆT ĐỐI chạy lệnh `python -c` mò mẫm từng toạ độ ADB trên terminal. Thao tác này gây chậm trễ, dễ click nhầm và làm gián đoạn hệ thống.
- **Tái sử dụng hàm chuẩn:** Luôn tái sử dụng trực tiếp hàm `get_s7_security_code` đã được kiểm chứng từ `D:\Taadaa\GPM auto\scripts\run_batch_login_6machines.py` (sử dụng `atx-agent` port 7912 và UI XML hierarchy).
- **Thứ tự ưu tiên xử lý Challenge:**
  1. **Ưu tiên 1 (IMAP Recovery Email OTP):** Nếu màn hình `challenge/selection` có tùy chọn gửi mã về `thanhdatbui1995@gmail.com` $\rightarrow$ Click chọn gửi mã về email khôi phục. Poll IMAP tự động lấy mã OTP 6 số. Cơ chế này nhanh hơn 10 lần so với S7 và không phụ thuộc vào tình trạng cáp/ADB của điện thoại thật (đặc biệt hiệu quả khi máy S7 bị offline như Máy 30).
  2. **Ưu tiên 2 (S7 Security Code 10 Số):** Nếu Google yêu cầu mã bảo mật Offline 10 số (`challenge/ootp`) hoặc Google Prompt (`challenge/dp`) mà không có tùy chọn mail khôi phục $\rightarrow$ Gọi `get_s7_security_code` với lock thiết bị.

---

## 2. Quy Chuẩn Bọc Device Lock Với `force_preempt=True`
Khi tương tác ADB với máy Samsung Galaxy S7 để trích xuất mã bảo mật:
```python
from automation_core.device_lock import acquire_device_lock

with acquire_device_lock(
    machine=str(machine_id),
    serial=serial,
    project="gpm-login",
    bypass_proxy_readiness=True,
    force_preempt=True
):
    try:
        # 1. Port forward ATX
        atx_port = 17000 + machine_id
        subprocess.run([ADB_EXE, "-s", serial, "forward", f"tcp:{atx_port}", "tcp:7912"], timeout=5)
        # 2. Mở Settings -> Google -> Tài khoản Google -> Bảo mật -> Mã bảo mật
        # 3. Trích xuất mã 10 số
    finally:
        # BẮT BUỘC: bấm Home (keyevent 3) để đưa máy về màn hình chính trước khi nhả lock
        subprocess.run([ADB_EXE, "-s", serial, "shell", "input", "keyevent", "3"], timeout=5)
```
- **Tại sao cần `force_preempt=True`:** Máy S7 có thể đang chạy cron nuôi TikTok hoặc feed session. `force_preempt=True` tạm dừng các worker khác để giành quyền điều khiển màn hình tức thì, ngăn ngừa xung đột UI và touch events.
- **Kỷ luật dọn dẹp:** Luôn đặt `keyevent 3` (HOME) trong khối `finally` trước khi rời context manager để màn hình S7 không bị kẹt ở menu Bảo mật của Google.

---

## 3. Lọc Nhiễu Khi Poll OTP IMAP `thanhdatbui1995@gmail.com`
Google tự động gửi rất nhiều email "Cảnh báo bảo mật" (Security Alerts) tới hòm thư khôi phục khi có đăng nhập từ thiết bị mới.
Nếu dùng hàm regex bóc 6 số chung chung trên toàn bộ email, script có thể bắt nhầm số trong email cảnh báo (ví dụ `000000`) thay vì mã xác minh thực sự.

### Giải pháp lọc chuẩn:
```python
def is_valid_otp_email(subject: str, body: str) -> bool:
    subj_clean = subject.lower()
    # Bỏ qua email cảnh báo bảo mật định kỳ
    if "cảnh báo bảo mật" in subj_clean or "security alert" in subj_clean:
        return False
    # Phải chứa từ khóa mã xác minh
    has_otp_keyword = any(kw in subj_clean for kw in [
        "mã xác minh", "verification code", "mã xác nhận", "mã của bạn"
    ]) or any(kw in body.lower() for kw in [
        "mã xác minh", "verification code", "mã xác nhận"
    ])
    return has_otp_keyword
```

### Pitfall Quan Trọng với `fetch_latest_otp` từ `read_otp_mail.py`:
Khi gọi `fetch_latest_otp(host="imap.gmail.com", user="thanhdatbui1995@gmail.com", ...)`, nếu hòm thư vừa nhận email *"Cảnh báo bảo mật nghiêm trọng cho ..."*, hàm `extract_otp_code` có thể parse ra chuỗi `'000000'`.
Nếu script không kiểm tra mà điền ngay vào ô input, Google sẽ báo lỗi sai mã OTP.
**Khắc phục bắt buộc khi gọi hàm:**
```python
otp_code = None
for _ in range(6):
    time.sleep(4)
    otp_res = fetch_latest_otp(
        host="imap.gmail.com",
        user="thanhdatbui1995@gmail.com",
        password=os.environ.get("OTP_MAIL_APP_PASSWORD", "zpxn wtmn bkgc adlc"),
        mailbox="INBOX",
        sender_hint="google",
        lookback_seconds=180,
        max_messages=10
    )
    # Bắt buộc lọc bỏ mã rác '000000' từ alert email
    if otp_res and otp_res[0] and otp_res[0] != "000000":
        otp_code = otp_res[0]
        break
```
- **Dynamic Lookback:** Khi bắt đầu kích hoạt gửi mã trên browser, ghi nhận `start_time = time.time()`. Chỉ nhận các email có `Date` timestamp $\ge start\_time - 15s$ để loại bỏ hoàn toàn các mã cũ của các phiên trước.
