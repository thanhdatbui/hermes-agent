# Hotmail Password Filtering: Snapshot Desync & Credential Domains

## 1. Hiện Tượng: "Vừa lọc lại mail xong sao vẫn báo sai pass?"

Khi người vận hành vừa lọc lại danh sách Hotmail (mua mới, đổi pass, hoặc kiểm tra live qua tool bên thứ ba) và cập nhật vào hệ thống nhưng vẫn thấy cảnh báo hoặc thắc mắc về lỗi "sai pass", cần lập tức kiểm tra 3 điểm nghẽn sau:

### A. Độ lệch thời gian giữa Snapshot báo cáo định kỳ và thời điểm lọc (Temporal Desync)
- **Cơ chế**: Các cronjob báo cáo định kỳ (ví dụ: `hotmail-gpm-lifecycle-6h-report` chạy mỗi 6h: 00:00, 06:00, 12:00, 18:00) đọc trực tiếp từ file state (`batch_gpm_5profiles_supervisor_state.json`).
- **Bẫy**: Nếu báo cáo 18:00 bắn ra thông báo danh sách đỏ 5 tài khoản `BLOCKED: Rate limit do thu sai mat khau`, nhưng đến 18:10 người vận hành mới nạp list mail đã lọc vào `hotmail_input.txt`, thì tin nhắn 18:00 hiển thị trên Telegram là **SNAPSHOT CŨ** trước khi cập nhật.
- **Triage O(1)**:
  1. Kiểm tra timestamp tạo báo cáo gần nhất trong `~/AppData/Local/hermes/cron/output/61570a1e37b1/`.
  2. So sánh với `mtime` của `D:/Taadaa/Hotmail/hotmail_input.txt` và `mtime` của `batch_gpm_5profiles_supervisor_state.json`.
  3. Kiểm tra trực tiếp trạng thái hiện tại trong `state.json`. Khi tài khoản đã nạp token/pass mới, supervisor tick tiếp theo sẽ giải phóng và chuyển sang `COMPLETED` hoặc `CHATGPT_REG`.

---

## 2. Phân Tách Triệt Để Các Miền Mật Khẩu (Credential Domains)

Hệ thống Taadaa Farm sử dụng 3 lớp mật khẩu độc lập trên cùng 1 tài khoản:

| Miền mật khẩu | File lưu trữ / Sổ gốc | Kênh thực thi | Hành vi khi sai |
| :--- | :--- | :--- | :--- |
| **Pass Mail (Hotmail/Outlook)** | `taikhoan_dat_v2_updated .xlsx` (cột 7), `hotmail_input.txt` (phần 2) | GPM Browser / Web Microsoft / IMAP | Microsoft báo `That password is incorrect` hoặc bắt verify email khôi phục. |
| **Pass TikTok** | `taikhoan_dat_v2_updated .xlsx` (cột 4), `taikhoan_run_safe.xlsx` | App TikTok trên Samsung S7 (ADB) | TikTok báo `Mật khẩu sai` (resource-id `id/ie1`) trên màn hình đăng nhập. |
| **Pass ChatGPT / OpenAI** | `taikhoan_dat_v2_updated .xlsx` (cột 12) | GPM Browser qua Playwright CDP | Form đăng nhập/đăng ký ChatGPT. |

**Quy tắc bất biến**:
- Lỗi "Mật khẩu sai" trên màn hình app TikTok (như Máy 53) là do **Pass TikTok** trong Excel bị lệch/sai, hoàn toàn KHÔNG liên quan đến việc Hotmail có sống hay đúng pass hay không.
- Không được nhầm lẫn giữa việc lọc sống/chết hòm thư Hotmail với việc tài khoản TikTok trên máy đó có đăng nhập được hay không.

---

## 3. Cơ Chế Token MS Graph Bypass Password Login

Trong `batch_gpm_5profiles_supervisor.py`:
- Nếu tài khoản có **OAuth Refresh Token** (định dạng `M.C...` trong `hotmail_input.txt`, `latest_bought_*.txt`, hoặc `gmail_clean_v2.xlsx`), hàm `load_state()` tự động:
  1. Nhận diện `has_token = True`.
  2. Tự động nâng `stage` từ `HOTMAIL_LOGIN` lên thẳng `CHATGPT_REG`.
  3. Xóa cờ `BLOCKED`/`FAILED` cũ và đưa về `PENDING` để chạy tiếp luồng ChatGPT.
- Nhờ cơ chế này, tài khoản có token Microsoft Graph API còn sống sẽ **không bao giờ phải gõ password trên giao diện Web Microsoft**, loại bỏ 100% rủi ro bị khóa do sai pass hoặc dính checkpoint xác minh email.
