# Quy tắc Xoay Vòng Quốc Gia 5SIM & Giới Hạn Rate Limit OpenAI khi Xác Minh Codex

## 1. User Rule & Kỷ luật cấu hình bắt buộc
> **Chỉ đạo cốt lõi của User:** *"1 quốc gia 3 lần, tối đa 3 quốc gia"*

- **Mỗi quốc gia:** Thử mua số và nhận OTP tối đa **3 lần** (`country_tries = 3`).
- **Tổng số quốc gia:** Tối đa **3 quốc gia** khác nhau trong một lượt chạy xác minh.
- **Tổng số lần mua số tối đa:** Không vượt quá $3 \times 3 = 9$ lần (thực tế thường dừng ở `max_attempts = 5` hoặc xoay đủ 3 nước).

## 2. Cơ chế Rate Limit & Phòng Chống Khóa Form của OpenAI
- **Hiện tượng khi spam 1 quốc gia / submit liên tục:**
  Sau 3 lần submit số điện thoại không thành công trên cùng một profile (do không có OTP, cancel số liên tục, hoặc format số bị từ chối), OpenAI sẽ kích hoạt cơ chế bảo vệ chống bot:
  - Form chuyển sang lỗi `phone_verification_dom_gate_failed`.
  - Hoặc phản hồi lỗi JSON parser: `Unexpected token "..." is not valid JSON`.
  - Profile bị tạm khóa nhập số điện thoại trong 24–48h.
- **Biện pháp phòng ngừa:**
  - Nếu một quốc gia thử 3 lần không có SMS hoặc không thành công $\rightarrow$ Bắt buộc dừng ngay quốc gia đó và xoay sang quốc gia kế tiếp trong pool giá rẻ ($\le 0.11\$$).
  - Không bao giờ retry cố định vào một quốc gia duy nhất quá 3 lần.
  - Hết 3 quốc gia mà vẫn chưa kích hoạt được $\rightarrow$ Đưa tài khoản về stage `WAIT_24_48H` để ngâm an toàn, tuyệt đối không cố chấp spam thêm.

## 3. Cơ chế Lazy Pool Cache Refresh Cooldown 1h (Chống Rate Limit 5SIM)
- **Vấn đề khi gọi API giá 5SIM liên tục:**
  - Nếu mỗi lần chạy worker đều quét toàn bộ bảng giá qua API `https://5sim.net/v1/guest/prices?product=openai`, khi chạy 5 worker song song hoặc supervisor loop liên tục sẽ làm nghẽn mạng và bị 5SIM chặn **HTTP 429 Too Many Requests**.
  - Nếu dùng cron cố định 4h/lần thì không kịp cập nhật các đợt nạp kho số mới.
- **Giải pháp tối ưu theo chỉ đạo User (Lazy Refresh with 1h TTL):**
  - Lưu cache tại `D:\Taadaa\runtime\kibe\cron-state\5sim_best_pools.json`.
  - Thiết lập hằng số `CACHE_TTL_SECONDS = 3600` (1 giờ).
  - Khi script chạy: kiểm tra `mtime` của cache.
    - Nếu cache đã cũ $> 1$ giờ: Gọi API 5SIM quét các nước giá $\le 0.12\$$, lọc kho sẵn $>20$ số, sắp xếp ưu tiên Việt Nam $\rightarrow$ `rate24h` cao nhất (Thái Lan, Argentina, Philippines, Anh...) và ghi đè cache.
    - Nếu cache còn hạn $< 1$ giờ: Đọc ngay từ file JSON ($<0.001$s), không gọi thêm request nào ra ngoài.

## 4. Bẫy Bản Địa Hóa Dropdown Quốc Gia OpenAI (Vietnamese Locale UI Trap)
- **Hiện tượng lỗi lệch nước:**
  - Trên các profile GPM chạy ngôn ngữ tiếng Việt (`vi-VN`), danh sách dropdown quốc gia của OpenAI hiển thị tên tiếng Việt thay vì tiếng Anh:
    - `GB` $\rightarrow$ *"Vương quốc Anh (+44)"* (nếu gõ *"United Kingdom"* sẽ rớt xuống *"Uganda (+256)"* gây hủy số oan).
    - `VN` $\rightarrow$ *"Việt Nam (+84)"*
    - `US` $\rightarrow$ *"Hoa Kỳ (+1)"*
    - `PH` $\rightarrow$ *"Philippines (+63)"*
    - `AR` $\rightarrow$ *"Argentina (+54)"*
    - `TH` $\rightarrow$ *"Thái Lan (+66)"*
- **Quy tắc chọn chuẩn xác:**
  - Bắt buộc xây dựng bảng ánh xạ `OPENAI_COUNTRY_MAP` theo từ khóa tiếng Việt không dấu:
    `{"VN": "Viet", "GB": "Vuong", "US": "Hoa K", "PH": "Phil", "AR": "Argen", "TH": "Thai"}`.
  - Mở listbox (`button[aria-haspopup="listbox"]`), gõ từ khóa, nhấn Enter, rồi kiểm tra `+<pfx>` trong text của nút. Nếu không khớp prefix thì hủy đơn và đổi nước, cấm submit sai quốc gia.

## 5. Kỷ luật Hoàn Tiền 100% Khi Hủy Số 5SIM
- 5SIM có chính sách hoàn tiền $100\%$ nếu đơn hàng được hủy trong vòng 90s khi chưa nhận được tin nhắn SMS.
- Khi gửi mã trên OpenAI: chờ tối đa 45s.
- Nếu sau 45s không thấy OTP trả về hoặc bị OpenAI báo lỗi số: lập tức gọi `GET https://5sim.net/v1/user/cancel/{order_id}` để hoàn lại toàn bộ số dư vào tài khoản trước khi thử số tiếp theo. Tuyệt đối không để đơn treo quá hạn trừ tiền.

