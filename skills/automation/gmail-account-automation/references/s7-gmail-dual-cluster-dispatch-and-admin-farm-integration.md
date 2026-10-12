# S7 Gmail Dual-Cluster Dispatch & Admin Farm Integration

**Ngày chốt:** 2026-10-12  
**Chỉ thị của Operator:** "Fix gọi luôn farm admin"

---

## 1. Bối Cảnh & Kiến Trúc Farm Kép (Dual-Farm)
- Trước 12/10/2026, Watchdog sau ca trưa (`post_noon_chain_watchdog.py`) chỉ chạy Phase 2 (TikTok 2FA) trên cả 2 cụm Kibe (Máy 1-80) và Admin (Máy 201-280).
- Phase 1 (Reg Gmail) trước đây chỉ gọi cục bộ trên máy Kibe qua `D:/Taadaa/register gmail/run_all.ps1`. Farm Admin bị bỏ trống slot reg Gmail dù file cấu hình `PROXYgandienthoai.xlsx` của Admin đã có đủ 80 máy (201-280).
- **Mục tiêu:** Kích hoạt mở rộng chạy song hành cả 2 cụm cho Phase 1, đồng bộ hóa với Phase 2 và chuẩn hóa báo cáo phân tách rõ ràng.

---

## 2. Kỹ Thuật Điều Phối SSH EncodedCommand Sang Farm Admin
Khi kích hoạt tiến trình PowerShell từ xa trên Windows (`admin-farm`) qua SSH:
1. **Tránh lỗi escape ký tự đường dẫn Windows:**
   - Dùng forward slash `./run_all.ps1` thay vì `.\run_all.ps1` (tránh `\r` bị parse thành Carriage Return làm đứt gãy lệnh).
2. **Nạp đầy đủ biến môi trường độc lập cho Admin:**
   ```powershell
   $env:PYTHONIOENCODING = 'utf-8'
   $env:PYTHONUTF8 = '1'
   Set-Location 'D:/Taadaa/register gmail'
   $env:PROXY_DIENTHOAI_PATH = 'D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx'
   $env:GMAIL_EXCEL_FILE = 'D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx'
   $env:PYTHONPATH = 'D:/Taadaa/register gmail;D:/Taadaa/automation-core/src'
   $env:GMAIL_REG_PYTHON_EXE = 'D:\Taadaa\python-envs\automation\Scripts\python.exe'
   & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ./run_all.ps1
   ```
3. **Đóng gói Base64 UTF-16LE (`EncodedCommand`):**
   - Lệnh được encode sang UTF-16LE base64 để truyền qua SSH argument an toàn tuyệt đối, không bị méo mó khoảng trắng hay ngoặc đơn trên command line.
4. **Xử lý Exception & Mã Lỗi Phân Tầng:**
   - Khi runner gặp exception (SSH timeout, rớt mạng), gán mã `kibe_code = 2` hoặc `admin_code = 2` và gắn nhãn lỗi có cấu trúc `RUNNER_ERROR|<CLUSTER>|<ExceptionName>: <exc>`.
   - Phân biệt rõ: Mã 1 là runner chạy có máy lỗi nền tảng (phone_verify, creation_error), mã 2 là runner crash/rớt mạng.

---

## 3. Chuẩn Hóa Báo Cáo Đối Xứng & Structured Telemetry
### A. Định dạng báo cáo đối xứng:
Khi phát hiện marker cluster trong output (`re.search(r"===\s*CLUSTER\s+ADMIN\b", g_out, re.I)`):
```text
[BÁO CÁO CHUỖI SAU CA TRƯA] [LANE ALL (GMAIL + TIKTOK 2FA)]
- Thời gian: 15:45 -> 16:40 (55 phút)
- Mã chạy (run_id): a1b2c3d4e5f6

- Phase 1 (Reg Gmail - Code 0):
  • Farm Kibe (Máy 1-80): Hoàn tất 5 máy | Bỏ qua 0 | Lỗi 10
  • Farm Admin (Máy 201-280): Hoàn tất 6 máy | Bỏ qua 0 | Lỗi 9

- Phase 2 (Add 2FA TikTok - Code 4):
  • Farm Kibe (Máy 1-80): Hoàn tất 12 máy | Bỏ qua 10 | Lỗi 52
  • Farm Admin (Máy 201-280): Hoàn tất 0 máy | Bỏ qua 59 | Lỗi 21
```

### B. Correlation ID & Structured Event Logging:
- Sinh `run_id = uuid.uuid4().hex[:12]` cho mỗi chuỗi chạy.
- Ghi log sự kiện có cấu trúc ra stderr:
  `WATCHDOG_EVENT {"ts": "...", "run_id": "...", "event": "chain_start|chain_end|cluster_runner_error", ...}`
- Giúp truy vết lỗi từng cluster và lưu `run_id` vào file state `post_noon_chain_state.json`.

---

## 4. Kiểm Hồi Quy (Regression Test Suite)
- Toàn bộ 29 test cases trong `tests/test_post_noon_chain_watchdog.py` bao phủ:
  1. Dual-cluster reporting cho cả Gmail và TikTok 2FA.
  2. Kịch bản 1 cluster chết (SSH timeout / runner crash) thì cluster còn lại vẫn hoàn thành.
  3. Kịch bản cả 2 cluster cùng chết phát đủ 2 event lỗi.
  4. Cơ chế lưu state `failed` khi có cluster lỗi và cho phép retry ở chu kỳ kế tiếp.
