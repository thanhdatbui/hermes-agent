# Quy Tắc Định Dạng Báo Cáo Farm Alert & Telegram (Clean Reporting)

## 1. Cấm Raw HTML Tags trong Cronjob stdout (Anti-Raw-HTML)
- Khi cronjob có `no_agent=True`, scheduler bắt stdout của script và gửi trực tiếp về Telegram.
- Nếu không đảm bảo parser Telegram parse HTML, các thẻ `<b>`, `</b>`, `<i>`, `<br>` sẽ bị lộ nguyên văn dưới dạng raw text trên màn hình điện thoại người dùng, gây cực kỳ khó chịu và mất thẩm mỹ.
- **Quy tắc:** Ưu tiên văn bản thuần sạch hoặc Markdown tự nhiên. Không nhét tag HTML thô vào các script watchdog/cron trừ khi gọi API Telegram chỉ định tường minh `parse_mode="HTML"`.

## 2. Tiêu Chuẩn Thẩm Mỹ & Trình Bày Gọn Gàng
- **Gom nhóm mục hoàn tất 100%:**
  + Không in lặp từng dòng riêng cho các Tik/hạng mục đã đạt 100%.
  + Gom chung vào 1 dòng: `  • Hoàn tất 100%: Tik 1, Tik 3, Tik 5, Tik 8`.
- **Loại bỏ mục trống:**
  + Không in các dòng `chưa gán nick (0/80 acc)` hay các Tik có 0 tài khoản. Mục nào không có dữ liệu cần ẩn đi để tránh làm loãng báo cáo.
- **Preview danh sách máy:**
  + Giới hạn tối đa 10 máy trong danh sách thiếu/lỗi: `preview = ", ".join(map(str, un[:10]))`.
  + **Bắt buộc có dấu cách sau dấu phẩy:** `", "` thay vì `","` để Telegram trên mobile tự động ngắt dòng tự nhiên, tránh tràn layout ngang.
  + Thêm hậu tố `... (+N)` nếu còn máy phía sau.

## 3. Kiến Trúc Báo Cáo Hai Cụm (Dual-Cluster Master Reporting)
- Báo cáo tổng kết toàn farm chạy từ máy Master (Kibe) phải gộp cả 2 cụm:
  + Header: `[FARM REPORT][TOÀN FARM] ...`
  + Khối 1: `🏢 【FARM KIBE - MÁY 1-80】`
  + Khối 2: `🏢 【FARM ADMIN - MÁY 201-280】`

## 4. Kỷ Luật Phản Hồi Trực Tiếp Với User (Anti-Tech-Dump & User-Centric Response)
- **CẤM TUYỆT ĐỐI xả dump kỹ thuật nội bộ:** Bảng điểm Closeout Gate (scorecard 85/100, judge notes), commit SHA, log pytest, stack trace, hoặc các thuật ngữ rào đón quy trình không được đưa vào câu trả lời trực tiếp cho Sếp trừ khi được yêu cầu rõ ràng.
- **Chỉ cung cấp kết quả nghiệp vụ cuối cùng:**
  + Đi thẳng vào 2-3 gạch đầu dòng giải thích bản chất: Vấn đề là gì -> Đã xử lý thế nào -> Kết quả thực tế (số liệu live, số máy, tài sản nick).
  + Khi Sếp phản ứng ngắn/thắc mắc ("3 bỏ qua an toàn là sao", "?????"): Tuyệt đối không trích dẫn quy trình bào chữa, phải lập tức giải thích bằng ngôn ngữ trực quan, ngắn gọn, dễ hiểu và đưa ra bảng đối soát cụ thể.

## 5. Chuẩn Hóa Phân Loại Lỗi Watchdog & Telemetry (Platform vs Script Errors)
- **Chỉ thị cốt lõi:** Lỗi script phải phân loại hoàn toàn khác lỗi nền tảng trong mọi báo cáo farm và file summary telemetry.
- **Nguyên tắc phân định:**
  + **Lỗi nền tảng (Platform / 3rd-party):** `phone_verify`, `account_creation_error`, captcha challenge, rate limit ➔ Do IP, thiết bị, fingerprint hoặc chính sách của Google/TikTok quét. Hướng giải quyết: xoay proxy, đổi dải IP, cho máy nghỉ cooldown.
  + **Lỗi script / kỹ thuật (Script / Automation):** `failed_cleanup` (lỗi thao tác UI Android gỡ acc), `failed_other` (script crash, exception, timeout, syntax bug) ➔ Do code automation của farm bị lỗi. Bắt buộc báo động đỏ (exit code 1) để kỹ thuật fix ngay, CẤM đổ thừa cho nền tảng và CẤM nuốt vào nhóm Bỏ qua an toàn (`SKIPPED`).
- **Mẫu báo cáo Telegram chuẩn hóa:**
  ```text
  • Đã hoàn tất: N máy
  • Bỏ qua an toàn: M máy (đầy slot / điều kiện an toàn)
  • Lỗi nền tảng (X): phone_verify: X, ...
  • Lỗi script (Y): failed_cleanup: Y, ...
  ```
- **Kỹ thuật Parser Tương Thích Ngược (SummaryResult Pattern):**
  + Khi refactor parser từ tuple `(total, success, failed)` sang dict có cấu trúc chi tiết, để tránh phá vỡ các caller hoặc test suite cũ đang unpack tuple `tot, suc, fail = parse(...)`:
  ```python
  class SummaryResult(dict):
      def __iter__(self):
          return iter((self.get("total", 0), self.get("success", 0), self.get("failed", 0)))
  ```
  + Nếu xóa bỏ một helper cũ (như `parse_chatgpt_warmup_counts`), bắt buộc giữ lại stub `def parse_chatgpt_warmup_counts(*a, **k): return 0, 0` để các test cũ hoặc external consumer không bị sập bởi `AttributeError`.
