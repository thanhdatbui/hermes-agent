# ChatGPT Web Pool Feeding, GPM Profile Sanitation & Proxy Governance

Tài liệu chuẩn hóa quy trình trích xuất session cookie ChatGPT Web từ kho profile GPMLogin, đối soát trạng thái đăng ký thực tế, và gán proxy vào OmniRoute pool (`chatgpt-web`).

---

## 1. Candidate Verification Invariant (Chống bốc nhầm acc chưa reg)

* **Bẫy dữ liệu:** Trong database GPMLogin (`profile_data.db`), tên profile thường có dạng `<stt> - <email> - <port>` (e.g. `01 - lipseybaroua@hotmail.com - 5101`). Tuy nhiên, sự tồn tại của profile trong GPM **không đồng nghĩa** tài khoản đó đã được đăng ký ChatGPT.
* **Quy tắc bắt buộc:**
  * TUYỆT ĐỐI KHÔNG query profile GPM thuần theo đuôi `@hotmail.com` / `@gmail.com` để nạp pool ChatGPT.
  * BẮT BUỘC cross-check danh sách email với state machine supervisor (`D:/Taadaa/runtime/admin/cron-state/batch_gpm_5profiles_supervisor_state.json` và `kibe/`):
    * **Nhóm ĐÃ REG HỢP LỆ:** `stage in ('DONE', 'WAIT_7D', 'CHANGE_INFO')` hoặc `chatgpt_registered_at IS NOT NULL`.
    * **Nhóm CHƯA REG:** Các tài khoản ở `stage: "HOTMAIL_LOGIN"` mới chỉ tạo profile và login email, chưa từng chạy đăng ký ChatGPT. Nếu nạp nhóm này, OpenAI coi là user mới và văng ra form `auth.openai.com/create-account/password`.

---

## 2. GPM SQLite Trash Trap (`GroupId == 0`)

* **Bẫy:** Bảng `Profiles` trong `profile_data.db` lưu trữ cả các profile đang hoạt động lẫn profile đã bị người dùng xóa vào thùng rác. Profile trong thùng rác có trường `GroupId = 0`.
* **Hậu quả:** Gọi API GPM `http://127.0.0.1:19995/api/v3/profiles/start/{pid}` với `GroupId == 0` sẽ trả về `PROFILE_IN_TRASH`. Script feeder mặc định retry 3 lần, làm nghẽn tiến trình và gây timeout hàng chục giây vô ích.
* **Khắc phục:** Luôn thêm điều kiện `WHERE GroupId != 0` (hoặc `GroupId > 0`) khi truy vấn profile ứng viên từ database GPM.

---

## 3. Port Regex Boundary Trap (Dải MobiProxy vs MikroTik)

* **Bẫy:** Nhiều script cũ dùng regex trích xuất port dạng:
  ```python
  m_port = re.search(r'(51\d\d|1000\d)', name)  # LỖI NGHIÊM TRỌNG!
  ```
  Regex `1000\d` chỉ bắt được các port từ `10000` đến `10009`. Toàn bộ 26 port MikroTik từ `10010` đến `10035` bị bỏ qua hoàn toàn, dẫn đến tình trạng script báo "hết ứng viên" trong khi kho vẫn còn hàng trăm profile MikroTik.
* **Khắc phục:** Bắt buộc dùng regex bao quát cả 4 chữ số (MobiProxy 5101–5138) và 5 chữ số (MikroTik 10001–10035):
  ```python
  m_port = re.search(r'(51\d\d|100\d\d)', name)
  ```

---

## 4. OmniRoute Proxy Quota & Assignment (Trần 2 acc / 1 IP)

* **Nguyên tắc phân bổ:** Mỗi proxy active trong `proxy_registry` chỉ được gán tối đa theo định mức User yêu cầu (mặc định trần $\le 2$ accounts / 1 IP).
* **Thuật toán cấp phát:**
  1. Đếm số lượng connection active hiện tại trên từng `proxy_id`:
     ```sql
     SELECT pa.proxy_id, count(pc.id)
     FROM proxy_assignments pa
     JOIN provider_connections pc ON pa.scope_id = pc.id
     WHERE pc.provider = 'chatgpt-web' AND pc.is_active = 1
     GROUP BY pa.proxy_id
     ```
  2. Tính số lượng cần bù: `needed = max(0, 2 - current_count)`. Nếu `needed == 0`, bỏ qua cổng đó ngay.
  3. Khi nạp thành công, bắt buộc ghi bản ghi vào `proxy_assignments` với `scope = 'account'`, `scope_id = connection.id`, `proxy_id = proxy.id` khớp đúng IP/port của profile GPM.

---

## 5. Fast Token Rescue vs. Expired Session Revival (OTP Graph API)

* **Quy trình 2 tầng:**
  1. **Tầng 1 (Fast Rescue - 3s/acc):**
     * Mở GPM profile qua CDP.
     * Đọc ngay cookie `__Secure-next-auth.session-token`. Nếu còn sống -> lưu ảnh Gate 6, sync vào OmniRoute, đóng dứt điểm profile GPM và dọn Chrome process ngầm để nhẹ máy.
     * Nếu cookie không tồn tại hoặc hết hạn -> không treo luồng đợi Google SSO; đóng profile chuyển ứng viên khác.
  2. **Tầng 2 (Revival qua Microsoft Graph API OTP):**
     * Khi tài khoản đã ngâm >14 ngày, session hết hạn, OpenAI chuyển hướng sang `auth.openai.com/email-verification` yêu cầu OTP 6 số gửi về Hotmail.
     * Nạp `refresh_token` và `client_id` từ `admin/gmail_clean_v2.xlsx` hoặc `kibe/gmail_clean_v2.xlsx`.
     * Sử dụng `MicrosoftGraphOTPProvider` kết nối endpoint Graph API `https://graph.microsoft.com/v1.0/me/messages` để bóc tách mã xác thực 6 số trong 1–2s.
     * **Lưu ý quan trọng:** Luôn truyền `received_after = datetime.now(timezone.utc) - timedelta(seconds=15)` hoặc lưu `seen_message_ids` khi fetch OTP, tránh đọc nhầm mã xác thực của các phiên đăng ký cũ trong quá khứ.
