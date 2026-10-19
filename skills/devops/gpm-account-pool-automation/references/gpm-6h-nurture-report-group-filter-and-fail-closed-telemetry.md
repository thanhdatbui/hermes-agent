# Chuẩn Hóa Báo Cáo 6H Nuôi Gmail GPM: Lọc Group 10 Fail-Closed, Phân Tách Cửa Sổ 6H và Cooldown 24H Cho NEEDS_LOGIN

Tài liệu chuẩn hóa kiến trúc báo cáo định kỳ 6h và cơ chế kiểm soát trạng thái session Google cho hệ thống nuôi tự động GPMLogin qua Playwright CDP.

---

## 1. Bản Chất Sự Cố Báo Cáo Ảo "79/77 Acc Văng Cookie" (19/10/2026)

### 1.1. Hiện tượng & Phản xạ Operator
- Bản tin định kỳ 6h (`cron_gpm_gmail_nurture_6h_report.py`) in thông số:
  ```text
  • Tổng số profile Group 10 (Google Live Ready): 77
  ⚠️ Acc phát hiện văng cookie (79 acc, đã đẩy re-login miễn trừ cooldown):
  ```
- **Nghịch lý toán học:** Tổng quy mô Group 10 chỉ có 77 profile nhưng lại báo 79 acc văng cookie.
- Operator lập tức phát lệnh: *"Fix lỗi đi"*.

### 1.2. Root Cause Analysis (3 Điểm Mù Kỹ Thuật)
1. **Bỏ quên lọc Group 10 (Unscoped State Scan):**
   - Script duyệt tuyến tính toàn bộ file `gpm_gmail_nurture_state.json`:
     ```python
     for em, info in state.items():
         if info.get("status") == "NEEDS_LOGIN":
             needs_login.append(em)
     ```
   - Trong 79 acc: có **29 acc lịch sử** từ các group cũ/đã xóa từ nhiều tuần trước và **50 acc** thuộc Group 10.
2. **Không áp cửa sổ thời gian 6h (Cumulative Historical Drift):**
   - Biến `nurtured_6h` có lọc theo `WINDOW_HOURS * 3600`, nhưng danh sách `needs_login` lại gom toàn bộ acc `NEEDS_LOGIN` từ đầu lịch sử (từ 08/10), khiến sự cố đã xử lý từ tuần trước vẫn bị lôi ra in thành "mới phát hiện văng cookie".
3. **Bẫy Nghẽn Vĩnh Viễn Trong Script Nuôi (`cron_gpm_gmail_nurture.py`):**
   - Vòng lặp chọn ứng viên `due_profiles` chứa đoạn code:
     ```python
     if info.get("status") == "NEEDS_LOGIN":
         continue
     ```
   - Cú `continue` vô điều kiện khiến mọi tài khoản một khi đã bị gắn cờ `NEEDS_LOGIN` thì bị loại vĩnh viễn khỏi hàng đợi nuôi, không bao giờ được bốc lại dù đã qua 10 ngày hoặc cookie đã được đăng nhập lại.

---

## 2. Quy Chuẩn Kỹ Thuật Bắt Buộc (Mechanical Invariants)

### 2.1. Truy Vấn Group 10 Thuần Read-Only & Fail-Closed
- **Chỉ mở Read-Only URI:**
  ```python
  conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
  try:
      rows = conn.execute(
          "SELECT Name FROM Profiles WHERE GroupId = ? OR GroupId = ?",
          (GROUP_ID, str(GROUP_ID))
      ).fetchall()
  finally:
      conn.close()
  ```
  *CẤM TUYỆT ĐỐI fallback mở SQLite ở chế độ ghi thông thường.*
- **Nguyên tắc Fail-Closed:**
  Nếu `group10_emails` rỗng hoặc lỗi kết nối, BẮT BUỘC bỏ qua toàn bộ state, không được để lọt tài khoản ngoài group:
  ```python
  # ĐÚNG (Fail-Closed):
  if not group10_emails or em_lower not in group10_emails:
      continue

  # SAI (Bẫy Fail-Open):
  if group10_emails and em_lower not in group10_emails:
      continue  # Nếu group10_emails rỗng thì dòng này bị bypass!
  ```

### 2.2. Phân Tách Rạch Ròi 2 Chỉ Số Cookie Trong Báo Cáo 6H
1. **Acc mới văng trong ca (`dropped_6h`):**
   - Chỉ đếm acc có `status == "NEEDS_LOGIN"` VÀ `(now_ts - last_checked) <= (WINDOW_HOURS * 3600)`.
   - Nếu bằng 0: in `• Trạng thái session 6h qua: ✓ Không có acc mới văng`.
2. **Tổng tồn đọng chờ re-login (`pending_relogin`):**
   - Đếm toàn bộ acc Group 10 đang có trạng thái `NEEDS_LOGIN`:
   - In: `⚠️ Tổng acc đang chờ re-login (Group 10): X acc (ưu tiên ca rảnh)`.

### 2.3. Lọc Chỉ Số Sản Lượng Nuôi `nurtured_6h` Theo `status == 'success'`
- Cấm chỉ đếm theo `last_nurtured` timestamp vì các lượt xử lý lỗi/crash có thể cập nhật timestamp nhưng chưa hoàn thành kịch bản.
  ```python
  if status == "success" and last_n > 0 and (now_ts - last_n) <= (WINDOW_HOURS * 3600):
      nurtured_6h += 1
  ```

### 2.4. Cooldown 24h Cho `NEEDS_LOGIN` Trong Hàng Đợi Nuôi
- Chuẩn hóa hằng số `NEEDS_LOGIN_COOLDOWN_SECONDS = 86400` (24 giờ).
- Logic chọn ứng viên:
  ```python
  status = info.get("status", "")
  if status == "NEEDS_LOGIN":
      last_checked = info.get("last_checked", 0)
      if (now_ts - last_checked) < NEEDS_LOGIN_COOLDOWN_SECONDS:
          continue  # Đang trong 24h chờ watchdog login, tạm bỏ qua
  
  # Hết 24h cooldown hoặc status != NEEDS_LOGIN: cho phép đưa vào due_profiles để tái thẩm định
  if (now_ts - last_nurtured) >= NURTURE_INTERVAL_SECONDS or status == "NEEDS_LOGIN":
      due_profiles.append((last_nurtured, p))
  ```

---

## 3. Quy Trình Kiểm Thử & Chống Hồi Quy (Test Verification)
1. **Kiểm tra ranh giới chính xác 24h:** Unit test assert tại đúng `now_ts - 86400` phải trả về `is_cooling_down == False`.
2. **Kiểm tra Fail-Closed:** Test trường hợp `group10_emails = set()` hoặc `None` phải đảm bảo `nurtured_6h == 0` và không lọt profile nào vào báo cáo.
3. **Kiểm tra lọc trạng thái thành công:** State chứa cả profile `success` và `failed` trong 6h qua thì `nurtured_6h` chỉ được ghi nhận đúng 1 lượt.
