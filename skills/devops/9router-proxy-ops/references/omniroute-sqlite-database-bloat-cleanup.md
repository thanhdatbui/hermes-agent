# Chẩn đoán & Xử lý OmniRoute SQLite Database Bloat & Crash

## 1. Triệu chứng & Hiện trường
- Hermes báo lỗi: `⚠️ The model provider failed after retries` khi gọi model qua OmniRoute cổng `:20129`.
- Cổng `192.168.110.123:20129` hoặc `127.0.0.1:20129` không phản hồi `/api/health` hoặc kết nối bị từ chối (`Connection refused`).
- Tiến trình OmniRoute bị chết liên tục sau 15–20 phút hoạt động, watchdog đếm lỗi restart liên tục.
- File DB `C:\Users\Kibe\.omniroute\storage.sqlite` phình to bất thường (1.5 GB - 7 GB) kèm file WAL `storage.sqlite-wal` cũng lên tới vài trăm MB - vài GB.
- Giao diện Dashboard (`/dashboard/logs`) mở trên trình duyệt bị trắng bóc (blank screen) do SSR/client query vào SQLite bị treo (HTML thô mất >9s, API client không hoàn tất).
- Endpoint `/v1/models` bị chậm bất thường (>10s) hoặc timeout (>20s).
- Endpoint `/api/health` phản hồi chậm (3s-5s thay vì <20ms) hoặc thỉnh thoảng rớt nhịp.
- Thư mục `C:\Users\Kibe\.omniroute\` tích tụ nhiều file `.bak` cũ chiếm tới 10–15 GB ổ C.

## 2. Nguyên nhân gốc rễ & Cạm bẫy chẩn đoán nhầm (Diagnostic Anti-Pattern)
1. **Phình dữ liệu các bảng lớn**:
   - Bảng `conversation_turn_nodes` (>1.5M rows), `quota_snapshots` (>400k rows), `xp_audit_log` (>250k rows), `call_logs` (>90k rows) và `agentic_conversations` tích tụ hàng triệu bản ghi.
   - OmniRoute không có background cron tự động dọn dẹp các bảng này.
2. **Synchronous I/O Block Event Loop**:
   - Khi Next.js dashboard query dữ liệu hoặc SQLite thực hiện WAL checkpoint / transaction commit trên file DB > 1.5GB, toàn bộ Event Loop đơn luồng của Node.js bị block cứng.
   - Hậu quả liên hoàn: `/dashboard/logs` trả về HTML mất 9–10s và client API không render được (màn hình trắng bóc), `/v1/models` timeout > 20s, `/api/health` mất 3s–5s hoặc timeout $\rightarrow$ Watchdog thấy 3 lần fail liên tiếp và restart tiến trình theo chu kỳ 20–25 phút.
3. **Bẫy chẩn đoán nhầm: "Do dead accounts làm chậm /v1/models và dashboard"**:
   - Khi soi log thấy ChatGPT-web 401 (hết hạn session cookie), Antigravity 429 (hết quota), hoặc proxy unreachable, người quan sát dễ kết luận nhầm rằng dead accounts làm chậm model-listing và dashboard.
   - **Thực tế**: Dead accounts CHỈ gây trễ retry combo (45s–78s per request) và spam thêm dòng lỗi vào `call_logs`. Thủ phạm DUY NHẤT khiến `/api/health` chậm và Dashboard trắng bóc là **Event Loop bị kẹt I/O do DB 1.5GB**.
4. **Lỗi "Decryption failed" trong log**:
   - Thường do credentials rác cũ từ các lần bootstrap trước đổi key, không phải mất key `STORAGE_ENCRYPTION_KEY` (key vẫn nằm nguyên vẹn trong `server.env`).
5. **Mất dấu nguyên nhân crash**:
   - Watchdog nguyên bản không chuyển hướng stdout/stderr của tiến trình node ra file, khiến crash không để lại trace trong Windows Event Viewer.

## 3. Quy trình khắc phục chuẩn hóa

### Bước 1: Giám sát stdout/stderr trong Watchdog
Sửa `omniroute_watchdog.ps1` để chạy node qua `cmd.exe /c` và chuyển hướng toàn bộ output vào file log:
```powershell
cmd.exe /c "node run-next.mjs >> logs\omniroute-stdout.log 2>&1"
```
Đồng thời thêm logic tự xoay vòng log khi file vượt quá 50MB.

### Bước 2: Dọn dẹp Database an toàn & Atomic Transaction
1. **Sao lưu trước khi dọn**: Copy `storage.sqlite` sang `storage.sqlite.bak_cleanup_<YYYYMMDD>`.
2. **Xóa bản ghi bằng Atomic Transaction (chống Partial Cleanup)**:
   Bọc cả 2 câu lệnh xóa trong `with conn:` của Python để nếu xảy ra lỗi ở bảng thứ hai hoặc database lock thì tự động rollback:
   ```python
   with conn:
       cursor.execute("DELETE FROM conversation_turn_nodes WHERE last_seen_at < ?", (cutoff_iso,))
       cursor.execute("DELETE FROM agentic_conversations WHERE last_seen_at < ?", (cutoff_iso,))
   ```
3. **Dồn WAL checkpoint an toàn**:
   - Nếu OmniRoute đang tắt: Chạy `VACUUM;` để co kích thước file SQLite vật lý.
   - Nếu OmniRoute đang chạy online: Sử dụng `PRAGMA wal_checkpoint(PASSIVE);` và `PRAGMA optimize;` để không gây lock exclusive lên các request LLM đang phục vụ.

### Bước 3: Dọn dẹp các file `.bak` cũ giải phóng ổ C
Chỉ giữ lại file backup gần nhất, xóa bỏ các file `.bak` cũ hơn 7 ngày để chống tràn ổ C. Tuyệt đối loại trừ các file đang hoạt động: `storage.sqlite`, `storage.sqlite-wal`, `storage.sqlite-shm`.

### Bước 4: Lập lịch tự động dọn định kỳ (Script `cleanup_omniroute_db.py`)
Triển khai script `cleanup_omniroute_db.py` chạy qua Cronjob Hermes vào 03:00 sáng Chủ Nhật hàng tuần:
- Schedule: `0 3 * * 0`
- Script: `cleanup_omniroute_db.py`
- Mode: `no_agent=True`, `deliver=local` (mô hình silent watchdog).
- **Telemetry Observability**: Ghi nhận metric `db_size_before`, `db_size_after`, `deleted_turn_nodes`, `deleted_conversations`, `elapsed_ms` vào `D:/Taadaa/runtime/audit_logs/omniroute_cleanup_audit.jsonl` (cấu hình linh hoạt qua `OMNIROUTE_AUDIT_LOG_DIR`).

### Bước 5: Kỷ luật Test Suite đạt chuẩn Sol Auditor
- Bắt buộc kiểm chứng cả 3 luồng:
  1. Xóa đúng bản ghi quá hạn và giữ lại bản ghi mới.
  2. Test khả năng **Atomic Rollback** khi có lỗi giữa transaction (ví dụ table missing hoặc constraint failure).
  3. Xóa đúng file `.bak` cũ quá hạn và không xóa nhầm file active DB.

---

## 5. Giải Mã Dashboard OmniRoute: Ký Hiệu "C" (Combo) & Độ Trễ Upstream Self-Healing
- **Biểu tượng chữ "C" màu vàng cam**: Đại diện cho **Combo Request** (request cha được bọc qua pipeline combo như `omni-worker`), tuyệt đối KHÔNG phải là lỗi "Cancelled".
- **Chu trình Self-Healing khi Upstream dính Token chết**:
  Khi tài khoản upstream (như Codex OAuth) bị hết hạn hoặc thu hồi token, OmniRoute sẽ tự động thử lại qua nhiều provider/tài khoản:
  1. Lần 1: Chờ phản hồi upstream quá 45s $\rightarrow$ văng `499` (Request aborted / timeout).
  2. Lần 2: Upstream trả về `401: Encountered invalidated oauth token for user`.
  3. Lần 3: OmniRoute tự chuyển sang token/tài khoản khả dụng khác và thành công $\rightarrow$ ghi nhận `200` kèm badge **`healed`**.
- **Độ trễ tích lũy**: Toàn bộ chuỗi 3 lần thử có thể ngâm từ **45s đến 78s** (hoặc request codex nặng ngâm 48s - 62s). Người dùng nhìn dashboard có thể lầm tưởng là server bị treo.
- **Kỷ luật điều tra**: Luôn tra cứu bảng `call_logs` trong `storage.sqlite` theo `correlation_id` hoặc khoảng thời gian để kiểm tra xem request cha/con đã trả về status 200 hay chưa trước khi phán đoán OmniRoute bị nghẽn.

