# GPM Proxy 1-1 Alignment cho Antigravity CLI Pool & Cơ chế Watchdog Chống Stale Quota

## 1. Kỷ luật Ánh xạ Proxy 1-1 (GPM Profile $\leftrightarrow$ Antigravity Sandbox Profile)

### Bối cảnh & Căn nguyên Lỗi:
Khi mở rộng dàn Antigravity CLI Pool từ 7 lên 22 profiles (`acc_01` .. `acc_22`), lỗi thường gặp của Coordinator là **gán proxy tuần tự** (`acc_01 -> mobi1`, `acc_02 -> mobi2`, `acc_03 -> mobi3`...).
- **Hậu quả:** Trong GPMLogin, mỗi tài khoản Google AI Pro được nuôi và đăng nhập trên một cổng proxy Mobi 4G cố định (ví dụ `dokieu04092004@gmail.com` ở GPM profile `09` dùng port `5111 - mobi11`). Nếu gán nhầm sang `5104`, Google sẽ phát hiện tài khoản phát sinh request từ một IP/Subnet hoàn toàn lạ so với lịch sử duyệt web -> Lập tức kích hoạt cơ chế chống gian lận `VALIDATION_REQUIRED` (403) hoặc checkpoint bảo mật.

### Quy tắc Vận hành Bắt buộc (Strict 1-1 Proxy Alignment):
1. **Truy vấn GPMLogin API (:19995):**
   - Quét danh sách profiles qua `GET /api/v3/profiles?page={N}&per_page=100`.
   - Tìm kiếm chính xác profile GPM chứa email hoặc username tương ứng.
   - Trích xuất trường `raw_proxy` chuẩn (ví dụ: `test.taadaa.click:5111:mobi11:TaadaaMobi#2026!`).
2. **Nạp vào `profiles_config.json`:**
   - Dùng script giải nén `D:/Taadaa/tools/unpack_omni_connection.py <email> <profile_name> <raw_proxy>` để ghi đúng URL proxy có encode mật khẩu (`%23` cho `#`, `%21` cho `!`).
3. **Audit Tiêu chuẩn Gói Pro:**
   - Chỉ nạp tài khoản có `provider_specific_data` chứa `tier: "g1-pro-tier"` / `Google AI Pro`. Tuyệt đối không nạp các tài khoản `free-tier`.
4. **Cô lập Đầy đủ Môi trường Sandbox:**
   - Mỗi profile phải có UUID `installation_id` ngẫu nhiên độc lập trong `.gemini/`.
   - Khởi tạo đầy đủ 3 thư mục: `AppData/Roaming`, `AppData/Local`, `Temp` để cách ly 100% cache Windows.

---

## 2. Cơ chế Watchdog Tự động Refresh Quota Claude CLI (Chống Stale Lockout)

### Triệu chứng & Nguyên nhân:
- `dispatch_worker.py` từ chối dispatch Claude Haiku với cảnh báo:
  `{"event": "quota_gate_triggered", "reason": "stale_quota", "fh": 5.0, "sd": 0.0, "role": "worker"}`
  mặc dù hạn mức 5h mới dùng 5% - 8% (còn 92% - 95% quota trống).
- **Nguyên nhân:** File `plan-usage-history.json` bị cũ quá 2 giờ (`MAX_QUOTA_STALE_HOURS = 2.0`), khiến hàm `get_claude_quota_status()` trong `claude_quota_guard.py` đánh giá dữ liệu mất hiệu lực và chặn nhầm.

### Giải pháp Khắc phục Triệt để:
1. **Script Refresh Quota:** `python D:/Taadaa/tools/refresh_claude_quota_file.py` tự động đọc trạng thái quota thực tế và ghi đè timestamp mới nhất vào `plan-usage-history.json`.
2. **Cronjob Watchdog Định kỳ 30 Phút (`refresh-claude-quota-watchdog`):**
   - Lập lịch chạy nền mỗi 30 phút (`*/30 * * * *`):
     ```bash
     python D:/Taadaa/tools/refresh_claude_quota_file.py
     ```
   - Giúp file lịch sử luôn tươi mới (<30 phút), đảm bảo Claude Haiku Worker luôn sẵn sàng phục vụ tác vụ code mà không bị gián đoạn.
