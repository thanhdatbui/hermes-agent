# False Alarm PREFLIGHT_VPN_BLOCKED, Stale Queue Accumulation & Workbook Boundary (2026-10-08)

## 1. Bản chất sự cố & Thắc mắc của Operator

Trong ca chạy avatar tối 08/10/2026:
1. Operator thắc mắc: *"Tik 4 vướng vpn là sao, máy k có vpn là sao làm gì có chuyện đó?"*
2. Operator bức xúc: *"Map 13 acc 1 máy là sao cái đéo gì thế?"*
3. Operator hỏi quy trình: *"Mà sao up avatar k dùng taikhoanrunsafe up mà cứ tự chế file v?"*

---

## 2. Root Cause 1: Bẫy Telemetry `[PREFLIGHT_VPN_BLOCKED]` do mất kết nối ADB/USB

### Cơ chế sinh lỗi:
- Trong `automation-core/src/automation_core/preflight.py` (dòng 708):
  Khi kiểm tra VPN trên thiết bị, nếu ADB bị mất kết nối (`device offline or ADB/USB disconnected: adb.exe: device not found`), hàm ném ngoại lệ:
  ```python
  raise ConsumerPreflightError(f"device is offline or ADB/USB disconnected for {serial_str}: {status.error}")
  ```
- Nhưng trong `Tiktok-video/scripts/tiktok_workflow/run_post.py` (dòng 1312–1325):
  Khối bắt lỗi gom chung toàn bộ `ConsumerPreflightError` thành:
  ```python
  except ConsumerPreflightError as cpe:
      logger.error(f"[PREFLIGHT_VPN_BLOCKED] device={device_id} vpn_required={vpn_required} error={cpe}")
      reporter.save_report({
          "status": "FAILED",
          "error_type": "PREFLIGHT_VPN_BLOCKED",
          "reason": f"[PREFLIGHT_VPN_BLOCKED] {cpe}",
      })
  ```
- **Hậu quả:** Thiết bị bị **tuột cáp USB / rớt socket ADB** (như M9, 10, 25, 38, 74, 77, 79), nhưng telemetry báo cáo ra ngoài Telegram lại là `[PREFLIGHT_VPN_BLOCKED]`. Điều này khiến Operator bức xúc vì nghĩ rằng proxy/VPN bị cấu hình sai hoặc thiếu, trong khi thực tế 100% máy đều đã gán proxy trong `PROXYgandienthoai.xlsx`.

### Quy tắc chẩn đoán O(1):
- Khi gặp `PREFLIGHT_VPN_BLOCKED`, kiểm tra ngay chi tiết chuỗi lỗi đằng sau:
  - Nếu chứa `device offline or ADB/USB disconnected` / `device not found` $\to$ **Lỗi socket ADB / phần cứng cáp USB**, KHÔNG PHẢI lỗi VPN.
  - Nếu chứa `required Android VPN is not connected` hoặc ping probe fail $\to$ Mới thực sự là lỗi kết nối mạng / proxy chưa thông.

---

## 3. Root Cause 2: Tích lũy nick rác "1 máy 13 acc" trong `avatar_replace_queue`

### Cơ chế sinh lỗi:
- Schema của bảng `avatar_replace_queue` trong `tiktok_tracker.db` có Primary Key là `(username, tik, host_id)`.
- Primary Key này **hoàn toàn không khóa bộ đôi `(may, tik)`**.
- Lịch sử vận hành:
  - Ngày 02/10: Nạp danh sách nick cũ của dàn Admin vào queue.
  - Ngày 07/10: Khi migrate sang 12 niche hot và chuẩn hóa danh sách nick theo các workbook `Tik1..8.xlsx` mới, các nick mới được `INSERT` vào queue.
  - Do PK không ràng buộc `may + tik`, các bản ghi cũ của ngày 02/10 **không bị xóa hay đè**, mà nằm song song cùng bản ghi mới của ngày 07/10.
  - Hậu quả: Máy 213 (và 256 slot khác trên Admin) bị gán tới **13 dòng nick** (6 nick cũ + 7 nick mới). Khi runner bốc nick cũ ngày 02/10 để chạy trên máy thật, nick đó không còn trên điện thoại $\to$ văng lỗi `ACCOUNT_SWITCHER_FAILED`.

### Quy trình dọn dẹp & Đối soát chuẩn (Reconciliation):
1. **Dọn rác lệch sổ cái chuẩn:**
   ```sql
   DELETE FROM avatar_replace_queue 
   WHERE rowid IN (
       SELECT q.rowid 
       FROM avatar_replace_queue q
       LEFT JOIN farm_account_info f ON q.may = f.may AND q.tik = f.tik AND q.username = f.username
       WHERE f.username IS NULL
   );
   ```
2. **Nạp bù nick còn thiếu từ `farm_account_info`:**
   ```sql
   INSERT OR IGNORE INTO avatar_replace_queue (username, may, tik, host_id, status)
   SELECT f.username, f.may, f.tik, f.host_id, 'PENDING'
   FROM farm_account_info f
   LEFT JOIN avatar_replace_queue q ON f.username = q.username AND f.may = q.may AND f.tik = q.tik
   WHERE q.username IS NULL AND f.username IS NOT NULL AND f.username != '';
   ```
3. **Đồng bộ cơ sở dữ liệu:**
   Chạy `scp D:/Taadaa/data/tiktok_tracker.db admin-farm:D:/Taadaa/data/tiktok_tracker.db` để máy trạm Admin có cùng dữ liệu sạch.

---

## 4. Phân định ranh giới Workbook: `taikhoan_run_safe.xlsx` vs `Tik1..Tik8.xlsx`

Khi Operator hỏi *"sao up avatar k dùng taikhoanrunsafe up mà cứ tự chế file v"*, Coordinator phải nắm vững ranh giới miền dữ liệu (Data Domain Boundary):

1. **`taikhoan_run_safe.xlsx` (hoặc `taikhoan_run_safe_combined.xlsx`):**
   - **Miền sử dụng:** Phục vụ luồng nuôi nick (`tiktok-luot nuoi acc`) và follow chéo (`tiktok-follow`).
   - **Cấu trúc:** Chỉ gồm 4–5 cột: `['May', 'Device ID', 'ID', 'Video Đã Đăng', 'Ngày Tạo']`.
   - **Thiếu sót trí mạng với Avatar:**
     - **Không có `Folder Video` (folder render) và `video gốc`:** Runner avatar bắt buộc phải biết nick đó liên kết với folder số mấy trên ổ D (`D:\video goc\<Folder>` và `D:\TIKTOK-videonuoinick\<Folder>`) để trích xuất ảnh nét hoặc bốc đúng ảnh `avatar.jpg`. Nếu chỉ có username, runner không biết lấy ảnh từ đâu.
     - **Không có phân chia Slot Tik:** Không phân biệt nick nào nằm ở app Tik 1, Tik 2... hay Tik 8 trên máy.
2. **`Tik1.xlsx` đến `Tik8.xlsx`:**
   - **Miền sử dụng:** Sổ cái phân bổ đầy đủ của toàn farm (nằm ở `OneDrive/TaadaaData/kibe` và `admin`).
   - **Cấu trúc:** `['Máy', 'device ID', 'ID', 'Folder Video', 'video gốc', 'Avatar Đã Up'...]`.
   - Đây là nguồn dữ liệu duy nhất cung cấp đầy đủ: máy nào, app Tik nào, username nào, tương ứng với Folder media nào trên đĩa để avatar runner vận hành chính xác.
