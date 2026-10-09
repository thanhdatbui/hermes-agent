# Gmail Missing Password Audit & Registration Merge Recovery

## 1. Bản Chất Sự Cố: Tài Khoản Reg Thành Công Nhưng Trống Mật Khẩu Trong Excel
Khi hệ thống vận hành đăng ký Gmail tự động trên dàn Samsung S7, các tài khoản được tạo thành công trên thiết bị và đã tạo GPM Profile tương ứng, nhưng cột `password` trong `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`, `Master_All`) hoặc `gmail_clean_v2.xlsx` lại bị trống (`None` / rỗng).

### Nguyên nhân kỹ thuật cốt lõi:
1. **Deprecation của Direct Excel Writes (`--write-workbook-success`)**:
   - Để tránh lỗi `PermissionError: [Errno 13]` do nhiều máy/tiến trình song song cùng tranh chấp quyền ghi file Excel (`master_gmail_manager.xlsx`), `gmail_reg_v10.py` đã vô hiệu hóa việc ghi trực tiếp vào workbook sau mỗi máy.
   - Thay vào đó, worker reg chỉ ghi kết quả cục bộ dạng JSON vào thư mục chỉ định qua tham số `--result-dir`.
2. **Đứt gãy khâu Merge sau ca (Post-batch Merge Gap)**:
   - Khâu gộp dữ liệu từ `--result-dir` vào Master Excel bị gián đoạn, timeout hoặc không được kích hoạt sau khi ca reg kết thúc.
   - Dẫn đến tình trạng email đã có trên thiết bị, profile GPM đã được tạo sẵn trên PC, nhưng Excel Master không có mật khẩu. Khi các cronjob như `gpm-oauth-full-pool-feeder` chạy, tài khoản bị phân loại nhầm thành `MISSING_PASSWORD` hoặc `SCRIPT_FAIL`.

---

## 2. Quy Trình 4 Tầng Truy Hồi Mật Khẩu Gốc (Password Recovery Runbook)

Khi phát hiện tài khoản Gmail thiếu mật khẩu trên Excel, **tuyệt đối không kết luận vội là mất pass hay xóa nick**, hãy thực hiện truy hồi theo 4 tầng:

### Tầng 1: Script Batch Khởi Tạo & Candidate Selectors
- Kiểm tra các file script điều phối batch trong `D:/Taadaa/GPM auto/scripts/`:
  - `run_batch_turn2_gmails.py` (chứa dict `TARGET_10_ACCOUNTS` map chính xác `email`, `pwd`, `machine`, `port`, `serial`).
  - `select_turn2_candidates.py`, `execute_m38_complete.py`, `solve_m38_correct_account.py`.
- Các file này thường lưu cứng danh sách tài khoản kèm mật khẩu sinh ra từ đợt reg hoặc lúc cấp phát.

### Tầng 2: GPM SQLite Database & Profile Creation Metadata
- Tra cứu database GPMLogin:
  `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
- Query:
  ```sql
  SELECT Id, Name, ProfilePath, RawProxy, CreatedAt 
  FROM Profiles 
  WHERE Name LIKE '%<username_hoặc_email>%'
  ```
- Tên profile GPM chuẩn có format: `<Machine_ID> - <email> - <Proxy_Port>`. Từ đây xác định được chính xác máy reg, port proxy và ngày giờ reg (`CreatedAt`).

### Tầng 3: Session Search Hermes & Live Transcripts
- Hermes lưu trữ các phiên can thiệp tay, direct signup và CDP login.
- Dùng `session_search(query="<email>")` để tìm lại anchor session ban đầu khi tài khoản được reg hoặc test login. Thường trong prompt hoặc tool call CDP sẽ có mật khẩu (ví dụ `@PhucThao01Lucky`, `PhamDuyYen@2002`).

### Tầng 4: Thư Mục Kết Quả JSON Tạm (`--result-dir`)
- Quét các thư mục lưu kết quả JSON tạm của `register-gmail`:
  - `D:/Taadaa/register-gmail/results/`
  - `C:/Users/Kibe/AppData/Local/register-gmail/results/`
- Mỗi file JSON lưu đầy đủ payload `{ "email": ..., "password": ..., "machine": ..., "created_at": ... }`.

---

## 3. Quy Trình Đồng Bộ Bù Mật Khẩu An Toàn (Dual-Excel Sync)
Sau khi truy hồi được mật khẩu chuẩn:
1. **Đồng bộ Master Excel (`master_gmail_manager.xlsx`)**:
   - Cập nhật cả 2 sheet: `Kibe_Farm_S7` và `Master_All`.
   - Ghi cột `password` (cột 3), cập nhật `trạng thái` = `LIVE`, và cột `cập nhật` = thời gian hiện tại.
2. **Đồng bộ Clean Excel (`gmail_clean_v2.xlsx`)**:
   - Sheet `Gmail Accounts`: Điền cột `pass mail` (cột 3), giữ nguyên proxy/machine mapping.
3. **Mở khóa trạng thái Feeder**:
   - Nếu tài khoản từng bị ghi nhận vào `failed_script_emails` trong `gpm_oauth_daily_state.json`, xóa email khỏi danh sách lỗi để cronjob Feeder bốc lại bình thường.
