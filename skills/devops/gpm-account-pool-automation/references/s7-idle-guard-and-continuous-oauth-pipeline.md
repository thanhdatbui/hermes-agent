# Canh Thiết Bị S7 Rảnh & Checkpoint Bypassing Khi Nạp OAuth GPM Hàng Loạt

## 1. Nguyên Tắc An Toàn: Canh Máy S7 Rảnh Tuyệt Đối (S7 Idle Gate)
Khi người dùng chỉ đạo: *"Canh S7 rảnh mới vào lấy mã nhé"*
- **Rủi ro tranh chấp thiết bị**: Máy Samsung S7 trong Farm thường xuyên chạy các cron nuôi TikTok / feed video. Nếu tiến trình nạp OAuth can thiệp ADB hoặc Google gửi Google Prompt trong khi app TikTok đang chiếm foreground:
  - App nuôi TikTok bị crash/mất tương tác.
  - Dialog Google Prompt hoặc màn hình mã bảo mật S7 không thể pop up hoặc bị đóng tức thì $\rightarrow$ fail nạp OAuth.
- **Quy trình kiểm tra O(1) trạng thái rảnh qua ADB trước khi dispatch worker**:
  ```python
  import subprocess

  def check_s7_idle(serial):
      adb = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
      r = subprocess.run([adb, "-s", serial, "shell", "dumpsys", "window", "windows"], capture_output=True, text=True)
      focused = [l.strip() for l in r.stdout.splitlines() if "mCurrentFocus" in l]
      f_str = focused[0] if focused else ""
      # Chỉ coi là RẢNH khi đang ở màn hình chính (Launcher) hoặc không có app nào chiếm focus
      is_idle = "com.sec.android.app.launcher" in f_str or "LauncherActivity" in f_str or not f_str
      return is_idle, f_str
  ```
- **Kỷ luật điều phối**: Nếu `is_idle == False`, Coordinator BẮT BUỘC bỏ qua máy đó trong lượt hiện tại, chuyển sang máy S7 khác đang rảnh (`LauncherActivity`), không được force stop app đang nuôi của Farm.

---

## 2. Chiến Lược Pre-flight Rà Soát Recovery Email Loại Trừ `khoaleemagic` O(1)
- Các tài khoản có email khôi phục chứa `khoalee` hoặc `khoalemagic` đã bị đưa vào chính sách cách ly của Farm.
- Khi worker chạy phải tài khoản dính `khoalee`, script sẽ tự động ngắt `SKIPPED_KHOALEE`.
- **Coordinator Pre-flight Gate**: Rà soát trước cột Recovery Email trong `master_gmail_manager.xlsx`:
  ```python
  if "khoalee" in rec_email.lower():
      # Skip ngay từ khâu chọn candidate, không dispatch worker lãng phí round-trip
      continue
  ```

---

## 3. Nhận Diện & Cô Lập Hard SMS Checkpoint Sau Khi Nhập TOTP
- **Hiện tượng**:
  - Script mở Profile GPM, nhập đúng Email, giải reCAPTCHA audio và điền đúng mã 2FA TOTP 6 số.
  - Tuy nhiên, Google vẫn tiếp tục chuyển hướng sang màn hình `challenge/iap` yêu cầu: *"Nhập số điện thoại để nhận tin nhắn văn bản cùng mã xác minh"*.
  - Bấm nút *"Thử cách khác"* nhưng Google không nhả ra phương thức Google Prompt hay Mã bảo mật S7.
- **Cơ chế xử lý chuẩn**:
  - Không cố retry liên tục trên cùng 1 tài khoản (sẽ đốt hết 15 iteration budget của worker).
  - Ghi nhận trạng thái `SMS_CHECKPOINT` / timeout vào `oauth_pipeline_status.json`.
  - Tự động cách ly tài khoản đó và tiếp tục luồng cuốn chiếu sang tài khoản tiếp theo có proxy live và S7 rảnh.

---

## 4. Kiểm Thử Pre-flight Upstream Proxy Singbox Bằng Playwright Trước Khi Dispatch
- Singbox port trên host `192.168.110.2` có thể đang mở socket TCP local nhưng modem 4G USB tương ứng bị rớt WAN (HTTP timeout).
- **Coordinator Pre-flight Check**: Chạy probe kiểm tra HTTP 200 thực tế:
  ```python
  from playwright.sync_api import sync_playwright

  with sync_playwright() as p:
      browser = p.chromium.launch(executable_path=CHROME_EXE, headless=True)
      page = browser.new_page(proxy={"server": f"http://192.168.110.2:{singbox_port}"})
      r = page.goto("https://accounts.google.com/ServiceLogin", timeout=5000)
      # Chỉ dispatch worker khi r.status == 200
      browser.close()
  ```
