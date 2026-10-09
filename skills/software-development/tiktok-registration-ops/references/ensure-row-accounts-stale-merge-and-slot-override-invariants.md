# Invariants Ghi Dữ Liệu Tracking Excel & Chống Trôi Slot / Duplicate (ensure_row_accounts.py)

## 1. Bản Chất 2 Lỗi Chí Mạng Đã Được Sol Auditor (GPT-5.6 Sol High) Chỉ Ra

### Lỗi 1: Stale Artifact Bug (Quét trôi ngược về quá khứ)
- **Cơ chế lỗi:**
  ```python
  dirs = sorted(runs_dir.glob("20*"), key=lambda d: d.stat().st_mtime, reverse=True)
  for d in dirs:
      found = sorted(d.glob("batch_*/stt_*/tracking_result_*.json"))
      if found:
          latest_run = d
          result_files = found
          break
  ```
- **Hậu quả:** Khi một đợt reg hiện tại **thất bại hoặc có 0 nick thành công**, thư mục run hiện tại không có file `tracking_result_*.json`. Vòng lặp `for d in dirs:` không dừng lại mà **chạy lùi về quá khứ**, bốc toàn bộ file kết quả của **đợt chạy trước đó (ví dụ cách 13-24 tiếng)** để merge lại vào Excel.
- **Invariant bắt buộc:**
  - `apply_results()` BẮT BUỘC nhận tham số `batch_start_time` (hoặc `target_run_dir`).
  - CHỈ được lọc các run directory có `st_mtime >= batch_start_time.timestamp() - 10`.
  - Nếu không có file mới nào trong batch hiện tại -> BÁO RỖNG VÀ THOÁT NGAY. TUYỆT ĐỐI CẤM loop lùi về các batch cũ.

---

### Lỗi 2: Slot Override Bug (Ép tham số dòng lệnh đè lên dữ liệu thật)
- **Cơ chế lỗi:**
  ```python
  slot = row if row in range(1, 9) else int(data.get("tik") or 1)
  target_row = (m - 1) * 8 + slot + 1
  ```
- **Hậu quả:** Khi chạy lệnh bù cho Row 5 nhưng bốc trúng file JSON của Row 7 (do lỗi Stale Artifact ở trên), code ép `slot = 5`. Nó lấy thông tin nick của Row 7 (`@gialan555`) ghi đè vào Folder/Slot của Row 5, tạo ra tình trạng 1 nick xuất hiện ở cả Row 5 và Row 7.
- **Invariant bắt buộc:**
  - Lấy đúng `slot` từ trường `tik` trong file JSON kết quả reg thật.
  - Nếu `json_slot != requested_row`: CẢNH BÁO và ưu tiên `json_slot`, KHÔNG ĐƯỢC ép `slot = row`.

---

## 2. Hard Guards Bắt Buộc Trước Khi Lưu Workbook

1. **Unique Constraint Guard (Chống Duplicate TikTok ID & Email):**
   - Trước khi ghi bất kỳ account nào vào `taikhoan_dat_v2_updated .xlsx`, quét toàn bộ sheet:
     - `existing_uids = {uid: row_index}`
     - `existing_mails = {mail: row_index}`
   - Nếu `uid` hoặc `mail` đã tồn tại ở dòng khác với `target_row`:
     - **REJECT NGAY LẬP TỨC** (`raise DuplicateAccountError` hoặc log REJECT và skip).
     - Tuyệt đối không cho phép 1 nick nằm ở 2 dòng khác nhau trong Master Workbook.

2. **Logical Row Lookup (Chống giả định vật lý `(m - 1) * 8`):**
   - Tìm chính xác dòng theo cặp `(Machine, Folder)`:
     Duyệt tìm dòng `r` có `Cột 1 == m` và `Cột 2 == folder_stt`.
   - Không được phụ thuộc vào công thức nhân cố định phòng trường hợp workbook bị xáo trộn thứ tự dòng.
