# Hotmail Lifecycle Reporting & Pre-filled Password Pitfalls

## 1. Bẫy dữ liệu: Mật khẩu điền sẵn vs Timestamp hoàn tất thực tế (Phantom Metric Pitfall)

### Vấn đề
Trong hệ thống tự động hóa vòng đời tài khoản Hotmail -> GPM -> ChatGPT -> Web Pool:
- File Excel nguồn (`taikhoan_dat_v2_updated .xlsx`) thường chuẩn hóa sẵn các cột mật khẩu dự kiến như `PASS MAIL`, `PASS CHATGPT` ngay từ khâu tạo phôi.
- Khi supervisor nạp tài khoản vào `state.json`, trường `chatgpt_password` được copy từ Excel sang profile object ngay từ giai đoạn khởi tạo (`stage: "HOTMAIL_LOGIN"`, `status: "PENDING"`).
- **Lỗi logic nghiêm trọng trong báo cáo định kỳ**:
  Nếu script báo cáo (ví dụ `cron_hotmail_gpm_lifecycle_6h_report.py`) tổng hợp tiến độ bằng cách kiểm tra:
  ```python
  # SAI LẦM: Coi việc có mật khẩu trong state là đã đăng ký thành công
  has_chatgpt = _has_valid_timestamp(raw, "chatgpt_registered_at") or bool(raw.get("chatgpt_password"))
  ```
  Hệ thống sẽ tính toàn bộ các tài khoản chưa hề đăng nhập Hotmail thành "Đã Reg ChatGPT Thành Công".
  *Hậu quả thực tế*: Farm Kibe mới chỉ login Hotmail được 86/409 tài khoản, nhưng báo cáo lại ghi nhận đã Reg ChatGPT 392/409 (báo khống +304 tài khoản, tỷ lệ ảo 83.7% thay vì 54.3% thực tế).

### Quy tắc bất biến (Reporting & Invariant Rule)
1. **Chỉ dùng Execution Timestamp & Post-Stages**:
   - Tài khoản CHỈ được tính là đã đăng ký ChatGPT khi:
     - Có timestamp thực thi hợp lệ: `chatgpt_registered_at` (chuỗi ISO datetime hợp lệ).
     - HOẶC profile đang ở các stage sau đăng ký: `stage in {"WAIT_7D", "CHANGE_INFO", "DONE"}` và `stage not in {"BLOCKED", "FAILED"}`.
   - Tuyệt đối KHÔNG dùng sự hiện diện của `chatgpt_password` hay `mail_password` làm căn cứ nghiệm thu trạng thái đã đăng ký.
2. **Quy tắc Kiểm tra Tính Nhất Quán Vòng Đời (Pipeline Monotonicity Check)**:
   - Trong chu kỳ tuần tự `HOTMAIL_LOGIN` -> `CHATGPT_REG`:
     `login_ok >= chatgpt_ok` luôn phải thỏa mãn ở mọi farm độc lập.
   - Nếu phát hiện `chatgpt_ok > login_ok` ở bất kỳ farm nào, script báo cáo hoặc telemetry phải phát warning `LIFECYCLE_ANOMALY_REG_EXCEEDS_LOGIN` ngay lập tức.

---

## 2. Tiêu chuẩn Báo cáo Vòng Đời 6H Đầy Đủ (4 Trụ Cột Cốt Lõi)

Một báo cáo vòng đời đạt chuẩn vận hành farm bắt buộc phải cung cấp đủ 4 khối thông tin:

### A. Phân rã tuổi ngâm `WAIT_7D` (Soaking Age Distribution & ETA)
- Không chỉ báo một con số gộp `Đang ngâm 7 ngày chờ đổi (WAIT_7D): N`.
- Phải bóc tách theo các bucket thời gian kể từ `chatgpt_registered_at`:
  - `< 1 ngày` (Mới vào hàng đợi)
  - `1 - 3 ngày`
  - `3 - 5 ngày`
  - `5 - 7 ngày` (Sắp chín - ETA đổi mật khẩu trong vòng 24 - 48h)
  - `>= 7 ngày` (Đã đủ điều kiện, sẵn sàng chuyển `CHANGE_INFO`)
- *Ý nghĩa*: Giải thích lý do vì sao `Hàng đợi đổi pass (CHANGE_INFO) = 0` (do chưa tài khoản nào đủ 7 ngày) thay vì để User hoang mang tưởng nhầm cron supervisor bị treo.

### B. Bóc tách nguyên nhân nhóm Kẹt / Cooldown (`BLOCKED`)
- Phân loại rõ các mã lỗi từ `last_result.detail`:
  - `Hotmail login that bai` (Kẹt challenge webmail Outlook, sai pass mail).
  - `GPM profile lookup / connection timeout` (GPM Local API sập hoặc quá tải port).
  - `Proxy / Network timeout` (Proxy rớt kết nối).
- Giúp Coordinator phân loại chính xác: đâu là lỗi transient cần retry (L0) và đâu là lỗi dữ liệu cần đổi tài khoản.

### C. Giám sát bước trung gian `CODEX_OAUTH` (5SIM Phone Verification)
- Khi pipeline có cờ bật/tắt dịch vụ ngoài (`ENABLE_CODEX_OAUTH`):
  - Phải hiển thị số tài khoản đã có `codex_oauth_at` (đã verify OTP SĐT VN thành công).
  - Nếu tính năng đang tạm tắt (do hết số hoặc tiết kiệm chi phí), phải ghi chú rõ trạng thái bypass sang `WAIT_7D`.

### D. Tỷ lệ Khai Thác Nạp Pool (Resource Utilization Ratio)
- Đối soát giữa số tài khoản đã reg (`chatgpt_ok`) với số connection đang nạp trong SQLite `storage.sqlite` (`SELECT count(*) FROM provider_connections WHERE provider='chatgpt-web'`).
- Báo cáo rõ: Tổng đã reg vs Đang active trên pool vs Đang soaking, tránh lãng phí tài khoản đã tạo nhưng chưa được đưa vào phục vụ.
