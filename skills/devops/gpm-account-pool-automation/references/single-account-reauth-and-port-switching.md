# Single Account Re-authentication & Port Switching Pitfalls

## 1. Tránh Early Return `ALREADY_SUCCESS`
File `oauth_pipeline_status.json` lưu cache các tài khoản đã từng nạp thành công vào OmniRoute:
```json
"omniroute_success": {
  "user@gmail.com": {
    "connection_id": "...",
    "port": 5113,
    "status": "HTTP_200_OK"
  }
}
```
Khi chạy hàm `process_account(acc)` trong pipeline `run_oauth_s7_pipeline.py`:
- Script sẽ đọc `STATUS_JSON` trước tiên.
- Nếu email có trong `omniroute_success`, nó return ngay `{"status": "ALREADY_SUCCESS", "conn_id": cid}` và KHÔNG thực hiện re-auth hay mở trình duyệt.
- **Giải pháp**:
  - Khi re-auth (đặc biệt là token expired cần refresh hoặc đổi port proxy/profile mới), phải xóa key email đó khỏi `omniroute_success` trong `oauth_pipeline_status.json` trước khi chạy, hoặc gọi trực tiếp pipeline logic với flag bỏ qua cache check.

## 2. Chỉ định Profile GPM và Port chính xác
- Trong DB SQLite của GPM (`profile_data.db`), một email có thể có nhiều profile lịch sử (ví dụ profile cũ port 5113, profile mới port 10020).
- Không dùng hàm `get_account_for_email(email)` thông thường vì hàm này dùng `SELECT ProfilePath FROM Profiles WHERE Name LIKE ?` không phân biệt được phiên bản profile mới hay cũ.
- Bắt buộc truyền payload trực tiếp vào `process_account(acc)`:
```python
acc = {
    "mid": 11,
    "email": "alicelmoralesjvcrj@gmail.com",
    "serial": "988633474f4b514436",
    "port": 10020,
    "singbox_port": 20020,  # 20000 + (port - 10000) đối với port 10000+
    "profile": "11-8801315697361_vdvbm",  # Thư mục profile chính xác
    "password": "...",
    "recovery": "...",
    "totp_secret": "...",
}
```

## 3. Singbox Port Mapping
- Playwright context khởi chạy với:
  `proxy={"server": "http://192.168.110.2:<singbox_port>"}`
- Công thức port:
  - Nếu port 5101..5199 -> `singbox_port = 20000 + (port - 5100)`
  - Nếu port 10001..10999 -> `singbox_port = 20000 + (port - 10000)` (ví dụ `10020` -> `20020`).
- Luôn kiểm tra curl test `http://192.168.110.2:20020` qua IP probe trước khi mở browser để tránh lỗi rớt mạng trong lúc trao đổi Authorization Code.
