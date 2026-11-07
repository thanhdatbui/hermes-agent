# Báo Cáo & Quy Chuẩn Xử Lý Sâu: CloudCode 403, Triệt Tiêu Chữ Ký Hermes Core & Tối Ưu Context Tail

## 1. Bản Chất Kỹ Thuật Gốc: Vì Sao Bị Bắn Lỗi 403 TOS_VIOLATION?
Lỗi `403 TOS_VIOLATION` trên endpoint `cloudcode-pa.googleapis.com` (Antigravity Cloud Code) không chỉ xuất phát từ một yếu tố đơn lẻ mà là **Multi-signal abuse detection** của Google:
1. **Chữ ký Hermes Agent cứng trong Core (Content Trigger):**
   - File `agent/system_prompt.py` của Hermes có lệnh: `stable_parts.append(HERMES_AGENT_HELP_GUIDANCE)`.
   - Chuỗi này chứa cố định: `"You run on Hermes Agent (by Nous Research)... https://hermes-agent.nousresearch.com/docs"`.
   - Dù chỉnh sửa `SOUL.md` sạch đến đâu, hàm build system prompt mặc định luôn tự nối chuỗi này vào payload trước khi gửi lên OmniRoute.
   - Khi payload chạm tới bot filter của Google, các chuỗi nhận diện bên thứ ba lập tức kích hoạt cờ ToS.
2. **Khác biệt TLS Fingerprint (Transport Signal):**
   - OmniRoute chạy trên runtime Node.js, TLS Fingerprint (JA3/JA4) và HTTP/2 frame settings lệch so với Antigravity IDE (chạy Go / BoringSSL native). Khi tài khoản gánh tải lớn, tín hiệu này kết hợp chữ ký text tạo thành chứng cứ 100% để Google khóa cổng API.
3. **Phân định rõ với `403 VALIDATION_REQUIRED`:**
   - `403 VALIDATION_REQUIRED` (như ca `votuyen1204200009`): Không phải ToS ban. Chỉ là session OAuth hết hạn do lâu ngày không hoạt động. Cần mở GPM login lại hoặc xác minh Security Code / Google Prompt trên điện thoại thật (Galaxy S7).

## 2. Quy Trình Kháng Nghị (Appeal SOP) Qua GPM Login + CDP
Khi acc dính `TOS_VIOLATION`:
1. Mở Profile GPM Chromium của đúng tài khoản đó qua API `:19995/api/v3/profiles/start/{id}` (giữ nguyên IP proxy của nick).
2. Kết nối CDP Playwright tới Chromium vừa mở.
3. Điều hướng tới Google Form chính thức: `https://forms.gle/hGzM9MEUv2azZsrb9` (Appeal Form — Terms of Service suspension for Antigravity, Gemini CLI, and Gemini Code Assist).
4. Do profile đã login Google, form tự nhận diện session: `Record <email> as the email to be included with my response`.
5. Tích chọn cam kết: `Yes, I understand` và bấm **Submit**.
6. Xác nhận bằng chứng màn hình WinRT OCR: *"Thanks. We will review your submission within 24 - 72 hours."*
7. Lưu ý: Google Form ghi dữ liệu vào Google Sheets của Google Trust & Safety, không gửi email đi nên mục **Sent (Đã gửi)** trong Gmail chắc chắn sẽ không có thư. Kết quả mở lại sẽ gửi về Inbox sau 24-72h.

## 3. Kiến Trúc Context Nén & Cân Bằng Prompt Cache vs Bandwidth Upload
- **Prompt Cache Hit (97.5%+):** Giúp Google không tính token tính toán cho prefix cũ và phản hồi nhanh (5s - 8s). Nhưng client vẫn phải upload toàn bộ JSON nặng vài MB qua mạng.
- **Nút thắt đường truyền 4G:** Payload trên 400k tokens qua proxy 4G chập chờn dễ bị drop kết nối, gây ra lỗi **HTTP 499 (Client Closed Request)** do timeout.
- **Cấu hình chuẩn trong `config.yaml`:**
  - `threshold: 0.3`: Giữ nguyên ở ngưỡng 300k tokens. Không nén quá sớm (< 150k) kẻo model mất chi tiết kỹ thuật ("Lost in the Middle").
  - `protect_last_n: 6`: Điểm vàng thực tế. Bảo vệ nguyên vẹn 3 lượt tool gần nhất để model đọc số liệu làm việc tức thời, trong khi các tool output cũ từ bước 4 trở về trước được rút ruột cơ học thành 1 dòng tóm tắt (`[terminal] ran <cmd> -> exit 0`), giải phóng ngay 50k - 80k tokens rác.
  - Tuyệt đối cấm đặt `protect_last_n: 0`: Khiến model không đọc được kết quả tool vừa chạy, rơi vào vòng lặp vô hạn (Infinite Tool Loop) hoặc hallucinate.
- **Cấu hình Combo trong OmniRoute (`storage.sqlite`):**
  - `strategy: least-used`: San phẳng tải trên dàn acc, tránh dồn hàng trăm call vào 1-2 nick.
  - `stickyRoundRobinLimit: 15`: Giữ affinity trong cùng 1 chuỗi hành động để ăn trọn prompt cache, sau đó tự động nhả ghim để xoay tua giải phóng tải.
