# Kỷ Luật Validate TikTok ID & Đối Soát Workbook Đồng Bộ (Chống Bẫy Drop Nick Thầm Lặng)

## 1. Bản Chất Sự Cố Đóng Băng Upload (Incident 2026-08-29 -> 2026-10-03)
- **Hiện tượng**: Nick `@vo.my.hanh94` (M69 Tik 1) và `@ngomai.ly` (M22 Tik 1) dừng đăng video từ tận 29/08 dù máy vẫn online và nuôi feed bình thường.
- **Gốc rễ sự cố**:
  - Khi dọn dẹp link rác `http://vo.my/...` trong `scripts/sync-tik-workbooks.py`, developer cũ đã viết code chặn theo kiểu substring ngây thơ:
    `if "vo.my" in s or "ngomai.ly" in s or "phng.th" in s: return False`
  - Biểu thức `"vo.my" in s` khớp trúng username hợp lệ `vo.my.hanh94`.
  - Cron đồng bộ 1 chiều chạy định kỳ đã tự động xóa trắng ô ID trong `Tik1.xlsx` và gắn nhãn `MISSING_ID`.
  - Runner upload (`run_tiktok_upload_batch.ps1` -> `account_source.py`) kiểm tra thấy ô ID TikTok bị `None` nên lập tức bỏ qua máy, khiến nick bị "đóng băng" đăng video suốt hơn 1 tháng mà không phát sinh exception nào.

## 2. Kỷ Luật Validate TikTok ID Chuẩn (Platform Spec Regex)
1. **CẤM TUYỆT ĐỐI**:
   - CẤM dùng `in` (substring containment) để lọc URL rác hoặc tên miền nếu chuỗi đó có thể trùng với phần tên của tài khoản người dùng (đặc biệt username tiếng Việt thường có họ/tên đệm chứa dấu chấm như `vo.my.hanh94`, `ngomai.ly`, `hanh.duong.11.22`).
   - CẤM hardcode blacklist username cá nhân vào logic validate hệ thống.
2. **Quy tắc chuẩn hóa `is_valid_tiktok_id`**:
   ```python
   import re

   TIKTOK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.]{2,24}$")
   DISALLOWED_PLACEHOLDERS = frozenset({
       "none", "null", "ghjfghj", "chua_co", "chưa có",
   })

   def is_valid_tiktok_id(val: object) -> bool:
       """Xác thực ID TikTok hợp lệ theo chuẩn platform, bảo toàn nick có dấu chấm."""
       if val is None:
           return False
       s = str(val).strip().lstrip("@")
       if not s or s.lower() in DISALLOWED_PLACEHOLDERS:
           return False
       if s.startswith("http://") or s.startswith("https://") or "/" in s or ":" in s:
           return False
       if s.isdigit():
           return False
       return bool(TIKTOK_ID_PATTERN.match(s))
   ```
   - Cho phép 2-24 ký tự gồm chữ cái, số, dấu gạch dưới `_` và dấu chấm `.`.
   - Chặn triệt để URL / đường dẫn qua ký tự phân tách đặc trưng: `/`, `:`, `http://`, `https://`.
   - Chặn ID toàn chữ số (`s.isdigit()`).
   - Lọc placeholder rác qua tập frozenset exact match.

## 3. Telemetry Rejection & Che Giấu Dữ Liệu Nhạy Cảm (Masking)
- Khi phát hiện ô có giá trị nhưng bị validator từ chối, bắt buộc ghi log telemetry có cấu trúc để dễ dàng truy vết và phát hiện bẫy:
  `[TELEMETRY_SYNC_REJECTED] Machine {m} Slot {slot}: rejected invalid TikTok ID '{masked}'`
- **Masking Invariant**: Để bảo vệ quyền riêng tư và an toàn tài khoản farm trong môi trường production, log KHÔNG ĐƯỢC in raw username mà bắt buộc mask:
  ```python
  def _mask_identifier(val: object) -> str:
      s = str(val or "").strip()
      if len(s) <= 4:
          return "***"
      return f"{s[:2]}***{s[-2:]}"
  ```

## 4. Quy Trình Đối Soát Toàn Farm Khi Phát Hiện Lệch ID (Fleet-Wide Audit)
Khi phát hiện bất kỳ nick nào bị mất ID hoặc gán `MISSING_ID` bất thường trên file Tik con:
1. **Quét đối soát 1:1 toàn bộ 8 file con vs Master DAT**:
   - Quét cả 2 cụm: `kibe` (Máy 1-80) và `admin` (Máy 201+).
   - Kiểm tra mọi slot 1..8 trên `Tik1.xlsx` .. `Tik8.xlsx` so với dòng tương ứng trong `taikhoan_dat_v2_updated .xlsx`.
   - Nếu Master DAT có ID mà Tik con bị `None` hoặc khác nhau: Báo động DISCREPANCY ngay lập tức.
2. **Chạy Validator kiểm chứng toàn diện**:
   - `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error`
   - `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/admin --exit-on-error`
   - Đảm bảo `0 lỗi FAIL, 0 cảnh báo WARN` (PASS 100%).
3. **Đồng bộ cơ sở dữ liệu `tiktok_tracker.db`**:
   - `python D:/Taadaa/tools/sync_farm_account_info.py`
   - Xác nhận đủ số lượng tài khoản (ví dụ 1.252 acc) và trạng thái mapping chính xác.
