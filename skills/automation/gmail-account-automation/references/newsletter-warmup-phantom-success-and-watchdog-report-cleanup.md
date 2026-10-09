# Newsletter Warmup Phantom Success, Watchdog Decommission Cleanup & Soak Rule (2026-10-01)

## 1. Kỷ Luật Tuyệt Đối Về Ngâm Gmail (Soak Aging Rule)
- **CẤM TUYỆT ĐỐI gợi ý hoặc thực hiện log Gmail lên GPM khi chưa ngâm đủ $\ge 7$ ngày trên S7** (kể cả với lý do bật 2FA, gắn recovery mail hay tăng trust).
- **Căn nguyên rủi ro (Google RBA):** Chuyển môi trường đột ngột từ Android ARM (S7) sang Windows x86 (GPM Chromium) trong vòng < 7 ngày sẽ bị hệ thống Risk-Based Authentication của Google đánh dấu hành vi buôn bán/chuyển giao acc tự động $\rightarrow$ Ép thẳng vào Phone Checkpoint (`challenge/iap`). Nếu không có SIM thật giải mã, nick sẽ DIE vĩnh viễn.
- **Dữ liệu thực nghiệm (2026-10-01):**
  + Các đợt ngâm $\ge 7$ ngày (22/09, 25/09): Tỷ lệ sống sót đạt **75% - 80%**.
  + Các đợt mới reg (26/09 - 01/10): Tỷ lệ quét của Google lên tới 55% - 85% trong 48h đầu. Nếu đưa lên GPM sớm, 100% nick bị quét DIE ngay.
  + Acc mới tạo BẮT BUỘC để yên tĩnh trên thiết bị S7, chỉ đồng bộ nền tự nhiên.

---

## 2. Bẫy Ngộ Nhận Thành Công Ảo (Phantom Success) Trong Newsletter Warmup
- **Hiện tượng:** Log runner báo `✓ [WARMUP_INBOX] Đã kích hoạt 4 dịch vụ newsletter gửi thư về <email>`, nhưng thực tế hộp thư Gmail trắng trơn, không nhận được bất kỳ email bản tin nào.
- **Căn nguyên kỹ thuật:**
  1. Trong `warmup_newsletter_services.py` và `subscribe_real_newsletter.py`: Các domain Cooperpress (`nodeweekly.com`, `javascriptweekly.com`, `rubyweekly.com`, `postgresweekly.com`) không tồn tại endpoint `/subscribe`.
  2. Gửi request POST vào `/subscribe` bị web server redirect (302/200) về trang chủ `/` HTML tĩnh.
  3. Thư viện `urllib.request.urlopen` tự động đi theo redirect, nhận HTTP 200 của trang chủ.
  4. Script kiểm tra lỏng lẻo `if resp.status in (200, 302, 303): success.append(name)` $\rightarrow$ ngộ nhận đăng ký thành công.
  5. Trong khi đó:
     - Form đăng ký thật của Cooperpress nằm tại `https://subscribe.cooperpress.email/start` với method `GET` và bị bảo vệ bởi Cloudflare Bot Detection (trả về HTTP 403 Forbidden).
     - Các dịch vụ khác (`Hacker Newsletter`, `Bytes.dev`, `React Digest`) đều đã đổi cấu trúc hoặc chết link, trả về HTTP 404 Not Found.
- **Bài học & Tiêu chuẩn:**
  - Không bao giờ dựa vào HTTP status code đơn thuần sau redirect để khẳng định hành động thành công.
  - Phải kiểm tra URL cuối cùng (`resp.geturl() == target_url`) và nội dung trả về (chứa thông báo "check your email", "subscribed successfully").
  - Nếu không có dịch vụ newsletter mở thật sự hoạt động, phải báo cáo trung thực hoặc gỡ bỏ hook, cấm giữ code log ảo gây hiểu lầm cho người vận hành.

---

## 3. Kỷ Luật Dọn Dẹp Telemetry Khi Decommission Tính Năng (Watchdog Report Cleanup)
- **Vấn đề:** Tính năng đăng ký ChatGPT trên S7 đã bị decommission hoàn toàn từ code runner (`gmail_reg_v10.py`), nhưng watchdog Telegram (`post_noon_chain_watchdog.py`) vẫn gửi thông báo:
  `* ChatGPT linked: telemetry riêng, không suy ra từ Gmail`
  làm User hiểu lầm rằng hệ thống vẫn đang lén lút chạy ChatGPT trên điện thoại.
- **Nguyên nhân:** Dòng template string bị hardcode trong script watchdog tổng hợp, kích hoạt dựa trên điều kiện `if g_suc > 0` thay vì đọc cờ thực tế từ runner.
- **Quy tắc bắt buộc:** Khi decommission bất kỳ tính năng hoặc hook nào:
  1. Gỡ logic trong core worker/runner (`gmail_reg_v10.py`).
  2. Rà soát và xóa sạch toàn bộ các dòng template text, hàm regex/parser phụ thuộc trong toàn bộ các watchdog cron script (`post_noon_chain_watchdog.py`, `feed_session_watchdog.py`, v.v.).
  3. Chạy test `--dry-run --force` kiểm tra format tin nhắn output trước khi kết thúc task.
  4. Đồng bộ ngay sang các thư mục phân phối (`deploy/hermes-home/scripts/` và `OneDrive/Taadaa_Sync_Shared/`).

---

## 4. Chuẩn Hóa Format Báo Cáo Watchdog & Phân Loại Lỗi (Platform vs Script Errors)
- **Chỉ thị của Sếp:** "Lỗi script phải phân loại khác lỗi nền tảng chứ" và báo cáo phải chuẩn hóa gọn gàng theo cặp chuẩn (`• Đã hoàn tất`, `• Bỏ qua an toàn`, `• Lỗi nền tảng`, `• Lỗi script`).
- **Ý nghĩa vận hành:**
  + **Lỗi nền tảng (Platform / Google):** `phone_verify`, `account_creation_error` ➔ Do IP, thiết bị hoặc Google quét RBA. Không phải do code hỏng; hướng xử lý là xoay proxy hoặc cooldown.
  + **Lỗi script / kỹ thuật (Script / Automation):** `failed_cleanup` (lỗi thao tác UI Android gỡ acc), `failed_other` (script crash, timeout, process ngắt) ➔ Lỗi code automation. Cần báo động đỏ để kỹ thuật fix ngay, cấm đổ thừa cho Google.
- **Chuẩn cấu trúc Telemetry trong `summary.json`:**
  ```json
  "failure_breakdown": {
    "platform_errors": {
      "phone_verify": 5,
      "account_creation_error": 0
    },
    "script_errors": {
      "failed_cleanup": 0,
      "failed_other": 0
    }
  }
  ```
- **Hàm phân tích tương thích ngược (Dual-Interface SummaryResult trong Watchdog Python):**
  - Tránh phá vỡ các caller cũ unpack `tot, suc, fail = parse_summary_counts(...)`:
  ```python
  class SummaryResult(dict):
      def __iter__(self):
          return iter((self.get("total", 0), self.get("success", 0), self.get("failed", 0)))
  ```
  - Stub an toàn cho các hàm helper bị decommission (chống `AttributeError`):
  ```python
  def parse_chatgpt_warmup_counts(log_dir_hint: Path | None = None, min_mtime: float | None = None) -> tuple[int, int]:
      """Deprecated: ChatGPT registration on S7 has been disabled."""
      return 0, 0
  ```
  - Bóc tách cấu trúc lỗi linh hoạt:
  ```python
  bk = data.get("failure_breakdown") or {}
  if "platform_errors" in bk or "script_errors" in bk:
      p_err = {k: v for k, v in bk.get("platform_errors", {}).items() if v > 0}
      s_err = {k: v for k, v in bk.get("script_errors", {}).items() if v > 0}
  else:
      p_err = {k: bk.get(k, 0) for k in ("phone_verify", "account_creation_error") if bk.get(k, 0) > 0}
      s_err = {k: bk.get(k, 0) for k in ("failed_cleanup", "failed_other") if bk.get(k, 0) > 0}
  ```
- **Mẫu hiển thị báo cáo Telegram chuẩn:**
  ```text
  [BÁO CÁO CHUỖI SAU CA TRƯA] [LANE GMAIL]
  - Thời gian: 15:15 -> 15:33 (18 phút)

  - Phase 1 (Reg Gmail - Code 0):
    • Đã hoàn tất: 7 máy
    • Bỏ qua an toàn: 3 máy (đầy slot)
    • Lỗi nền tảng (5): phone_verify: 5
    • Lỗi script: 0
  ```
- **Đồng bộ 3 vị trí:** Bắt buộc đồng bộ file watchdog script qua cả 3 nơi:
  1. `C:/Users/Kibe/AppData/Local/hermes/scripts/` (Runtime local của Kibe)
  2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/` (Git repository deploy)
  3. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/` (OneDrive phân phối toàn farm)

