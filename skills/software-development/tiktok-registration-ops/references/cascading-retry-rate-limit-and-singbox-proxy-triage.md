# Cascading Retry Rate-Limit & Sing-box Proxy Triage (TikTok Reg)

## 1. Triệu chứng lỗi
- Dưới ô nhập email xuất hiện thông báo đỏ:
  `Please try again or log in with a different method.`
- Hiện tượng: Script bị timeout ở bước [9] chờ login success và văng alert giữ hiện trường máy.

## 2. Bản chất kỹ thuật & Cơ chế gây lỗi (Root Cause)
Lỗi này thường là kết quả của **2 vấn đề cộng hưởng**:

### A. Sập kết nối Upstream Proxy (Single-port Sing-box)
- Thiết bị Android trên farm được gán proxy cố định: `192.168.110.2:20000+N` (Máy N).
- Port `20000+N` được điều phối bởi Sing-box trên router MikroTik (`192.168.110.2`), chuyển tiếp (outbound) tới proxy đích (ví dụ: `test.taadaa.click:51XX` với user `mobiX`).
- Khi upstream proxy (`test.taadaa.click:51XX`) bị sập hoặc từ chối kết nối (`Connection Refused` / `Reset`):
  + Wi-Fi của máy vẫn sống 100% (ping router, ping gateway, link speed bình thường).
  + Nhưng toàn bộ HTTP/HTTPS traffic bị nghẽn qua proxy.
  + Status bar của Android hiện cảnh báo: `Tín hiệu Wi-Fi đủ., Không có Internet` (do Android Captive Portal check qua proxy bị timeout).
  + App TikTok gửi request submit email đi nhưng không nhận được phản hồi (stalled).

### B. Cascading Retries trong Script (`social_reg_v1.py`)
- Khi request submit lần 1 ở bước [7] (`fill_email_and_next`) bị treo hoặc không chuyển màn:
  + Script timeout nhận diện kết quả và rơi vào `unknown fallback`.
  + Bước [7c] kiểm tra màn hình, thấy vẫn còn text *"Nhập địa chỉ email"* và nút *"Tiếp tục"*, tưởng nhầm là màn confirm email lần 2 $\rightarrow$ gõ lại và bấm *"Tiếp tục"* **lần 2**.
  + Bước [8b-0] (`handle_post_auth_screens`) tiếp tục quét màn hình, thấy vẫn ở form email $\rightarrow$ gõ lại và bấm *"Tiếp tục"* **lần 3**.
- **Kết quả:** Bấm nút *"Tiếp tục"* dồn dập 3 lần trong vòng 2 phút trên cùng 1 IP/thiết bị khiến backend TikTok kích hoạt cơ chế bảo vệ chống spam (Rate-limit) $\rightarrow$ Hiện thông báo đỏ chặn đăng nhập/đăng ký bằng phương thức email này.

## 3. Quy trình Triage nhanh O(1)

### Bước 1: Kiểm tra Proxy Port trên máy
```bash
# Lấy proxy đang gán trên máy N
adb -s <serial> shell settings get global http_proxy
```

### Bước 2: Truy vết Mapping Sing-box
Mở file `D:/Taadaa/AI-Tools/config/singbox_config.json`:
- Tìm inbound có `listen_port`: `20000+N` $\rightarrow$ tag `mixed-m<N>`.
- Tìm route rule: `inbound: ["mixed-m<N>"]` $\rightarrow$ `outbound: "proxy_m<N>"`.
- Đọc thông số outbound: `server`, `server_port`, `username`, `password`.

### Bước 3: Test Upstream trực tiếp
Thử kết nối thẳng vào server upstream qua Python script ngắn hoặc curl để cô lập nguyên nhân:
- Nếu upstream trả về `WinError 10061 (Connection Refused)`: Lỗi tại nhà mạng/proxy provider upstream sập cụm port.
- Không phải do sập Wi-Fi router.

## 4. Biện pháp xử lý & Phòng tránh
1. **Không retry ngay:** Khi đã bị dính lỗi đỏ rate-limit, tuyệt đối không chạy Canary spam lại ngay trên cùng email/IP để tránh bị block vĩnh viễn nick/IP.
2. **Khôi phục upstream proxy:** Đổi proxy port hoặc liên hệ reset port trên `test.taadaa.click`.
3. **Chặn cascading retries trong code:** Cần có state check sau khi submit email ở bước [7]; nếu vẫn còn ở form cũ sau timeout thì fail-closed và dừng lại, không để bước [7c] và [8b] tự ý bấm lại nút "Tiếp tục".
