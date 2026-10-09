# Aged Gmail SMS Checkpoint Pathology & Watchdog Stdout Discipline

Tài liệu đúc kết từ sự cố rò rỉ log ra Farm Alert và điều tra nguồn gốc 59 Gmail ngâm lâu (2–6 tháng) bị Google khóa đòi số điện thoại (SMS Checkpoint).

---

## I. Kỷ Luật Stdout Cho Cronjob Watchdog (`no_agent: true`)

### 1. Cơ chế vận hành của Hermes Cronjob
- Đối với cronjob cấu hình `no_agent: true`, scheduler thực thi script Python định kỳ và **bốc toàn bộ nội dung xuất ra `sys.stdout` gửi nguyên văn về kênh đích** (Telegram Farm Alert).
- Nếu `stdout` rỗng: scheduler im lặng (Silent Watchdog) — không gửi tin nhắn.
- Nếu `stdout` có bất kỳ ký tự nào: scheduler gửi tin nhắn về chat.

### 2. Cạm bẫy rò rỉ log từ thư viện / module con
- **Nguyên nhân sự cố**: Script chính (`sync_gpm_lifecycle.py`) import module phụ (`preflight_s7_rolling_cleanup.py`). Trong module phụ có dòng khai báo ở module-level:
  ```python
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s [%(levelname)s] %(message)s",
      handlers=[logging.StreamHandler(sys.stdout)]  # <-- LỖI NẶNG!
  )
  ```
- **Hậu quả**: Khi module phụ được import, nó gán `StreamHandler(sys.stdout)` vào **Root Logger**. Toàn bộ các thư viện khác (như `automation_core.adb`, `requests`, ADB client, dumpsys) khi ghi log `logger.info(...)` đều bị đẩy ra root logger và tuôn thẳng vào `sys.stdout`, làm tràn hàng chục dòng log debug (`AdbClient initialized...`, `dumpsys account...`, `Máy M07 đang trong slot feed, bỏ qua...`) vào Farm Alert mỗi 15 phút.

### 3. Quy tắc lập trình chuẩn cho Module & Watchdog
1. **Module con / helper**:
   - **TUYỆT ĐỐI CẤM** gọi `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ở cấp độ module.
   - Luôn sử dụng logger riêng (`logger = logging.getLogger(__name__)`), set `logger.propagate = False`, và ghi log vào `FileHandler`.
   - Nếu chạy CLI trực tiếp (`if __name__ == '__main__':`), chỉ gán `StreamHandler(sys.stderr)` để console quan sát được mà không làm ô nhiễm `sys.stdout`.
2. **Caller / Watchdog chính**:
   - Chủ động dọn sạch handler stdout khỏi root logger trước và sau khi import các module khác:
     ```python
     root_logger = logging.getLogger()
     for h in list(root_logger.handlers):
         if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) in (sys.stdout, sys.__stdout__):
             root_logger.removeHandler(h)
     ```
   - Chỉ dùng `print()` đúng 1 dòng tóm tắt duy nhất khi có kết quả thực tế phát sinh (vd: `[GPM & S7 LIFECYCLE] Tạo mới X profile | Đã dọn Y tài khoản`).
   - Khi không có thay đổi: giữ `stdout` rỗng 100%.

---

## II. Bệnh Lý Aged Gmail Dính Checkpoint SĐT (SMS Checkpoint Pathology)

### 1. Bản chất gốc của Gmail Farm
- Các tài khoản Gmail reg trên Samsung S7 bằng tool tự động là dạng **Bypass Phone** (bỏ qua số điện thoại).
- Đối với hệ thống chống gian lận của Google: Tài khoản không có SĐT là tài khoản **chưa hoàn tất định danh** (Unverified Identity). Google tạm chấp nhận tài khoản tồn tại nhờ vào **Hardware Trust Anchor** (mỏ neo phần cứng của chiếc Samsung S7 kèm tín hiệu heartbeat định kỳ của Google Play Services).
- Tuổi đời (2 tháng hay 6 tháng) chỉ giúp tài khoản qua được đợt quét diệt bot 48h đầu trên S7, **hoàn toàn không biến tài khoản thành tài khoản an toàn tuyệt đối**.

### 2. Bốn (04) hành vi bất thường kích hoạt SMS Checkpoint

| STT | Hành vi bất thường | Cơ chế kích hoạt cảnh báo của Google | Hậu quả thực tế |
|---|---|---|---|
| **1** | **Chùm mail khôi phục (Recovery Cluster)** | 1 địa chỉ email (vd: `thanhdatbui1995@gmail.com`) làm mail khôi phục cho **149 tài khoản**. Khi 1-2 tài khoản trong chùm có biến động, AI của Google quét đồ thị liên kết (Cluster Graph) và siết checkpoint đồng loạt toàn bộ chùm. | Hàng chục acc cùng die dù không hoạt động gì. |
| **2** | **Nhảy môi trường đột ngột (Device / Canvas Jump)** | Tài khoản nằm yên nhiều tháng trên Android S7 bỗng nhiên đăng nhập trên PC Windows (GPMLogin Chrome) với Canvas, WebGL, Audio, Screen resolution hoàn toàn mới. | Google gắn cờ "Thiết bị lạ / Nghi ngờ chiếm đoạt tài khoản". |
| **3** | **Đá văng mỏ neo phần cứng S7 (`device-activity`)** | Script tự ý vào `https://myaccount.google.com/device-activity` bấm **"Đăng xuất" (Sign out) Galaxy S7** để cố xóa dòng "Lời nhắc của Google". | **TÍNH CHẤT NGUY CẤP SỐ 1**: Session PC mới toanh vừa đăng nhập đã đá văng thiết bị điện thoại mỏ neo ban đầu. Thuật toán Google xếp vào diện **Account Takeover (Cướp tài khoản)** $\rightarrow$ Khóa ngay lập tức, bắt xác minh SMS qua SĐT. |
| **4** | **Bão Google SSO & reCAPTCHA loops** | Chạy batch 5 workers đồng thời mở Google SSO (`accounts.google.com/v3/signin/...`) cào session ChatGPT-Web trên cùng dải IP, dính Audio reCAPTCHA và giải đi giải lại liên tục. | Khi tài khoản dính reCAPTCHA quá nhiều lần, Google nâng mức trừng phạt từ reCAPTCHA lên **SMS Checkpoint cưỡng chế**. |

### 3. Nguyên tắc vận hành bảo vệ tài sản Farm
1. **CẤM TUYỆT ĐỐI vào `device-activity` đăng xuất Samsung S7**:
   - Muốn không bị hỏi prompt S7 trên PC: Phải dùng phương thức 2FA TOTP (Google Authenticator) qua nút *"Thử cách khác"* (Try another way) $\rightarrow$ Điền mã 6 số từ `pyotp`. Tuyệt đối không xóa S7.
2. **CẤM bốc ồ ạt Gmail Farm S7 lên PC**:
   - Mỗi máy S7 chỉ gán 1:1 với 1 profile GPM tương ứng qua đúng cổng Proxy di động của máy đó.
   - Phải có thời gian làm ấm (warm-up): xem YouTube, đọc News, search tự nhiên trước khi thực hiện các thao tác bảo mật nhạy cảm.
3. **Phân tán mail khôi phục**:
   - Khi reg tài khoản mới, không dồn hàng trăm acc vào duy nhất 1 email khôi phục.
4. **Hạ trần Concurrency (Tối đa 2 workers)**:
   - Các batch liên quan đến Google login / OAuth chỉ chạy tối đa 2 workers song song, có stagger 10–15s và jitter để tránh kích hoạt reCAPTCHA bão trên dải IP 4G.
