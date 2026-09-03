# Cohort Target Identity Validation Rules

## Bối cảnh & Nguyên nhân lỗi `missing:tik`
Khi triển khai validation frozen cohort binding trong `_apply_cohort_identity` (`flows/multi_machine_feed_session.py`):
- Trước đó, code kiểm tra bắt buộc trường `"tik"` phải có mặt trong `expected` entry (`if "tik" not in expected: mismatches.append("missing:tik")`).
- Tuy nhiên, assignment manifest thực tế từ cron picker / manifest generator chuẩn chỉ chứa `machine`, `serial`, `account`, `account_row`, `session_index`, `feed`... mà không nhất thiết phải có field `"tik"` ở root entry.
- Kết quả: Khi cron dispatch batch feed, các worker chạy vào `_apply_cohort_identity` bị fail-closed với lỗi `cohort target identity mismatch: missing:tik`, gây dừng phiên toàn bộ máy trong cohort dù thông tin account, serial, machine hoàn toàn khớp.

## Quy tắc thiết kế Cohort Identity Binding
1. **Trường bắt buộc (Strict Canonical Fields):**
   - `machine`: int, phải khớp chính xác `account.machine`.
   - `account_row`: int, phải khớp chính xác `account.account_row_index`.
   - `serial`: str non-empty, khớp chính xác `account.serial`.
   - `account`: str, sau khi lstrip("@") phải khớp `account.expected_username`.
   - `feed`: Mapping chứa `row` (int) và `machines` (list[int] độ dài 1).

2. **Trường tùy chọn (Optional Matching):**
   - `"tik"` ở root entry hoặc trong `"target"` sub-mapping: **Chỉ validate khi trường này tồn tại trong entry** (`if "tik" in expected:` / `if "tik" in target:`). Tuyệt đối không append `"missing:tik"` nếu entry không có key `"tik"`.
   - `"target"`, `"lock"` sub-mappings: Chỉ validate các nested fields khi key tương ứng xuất hiện trong `expected`.

3. **Kiểm tra khi sửa đổi Cohort Validator:**
   - Luôn chạy test suite với các fixture manifest tối giản (chỉ gồm các trường canonical không có `"tik"`), đảm bảo tương thích ngược với mọi generator manifest.

## Bối cảnh & Triage lỗi `expected_username` do Mid-day Workbook Drift
- **Hiện tượng:** Máy dừng phiên với lỗi `cohort target identity mismatch: expected_username` khi chạy feed session.
- **Nguyên nhân gốc:**
  1. Cron khởi tạo đầu ngày đóng băng snapshot / cohort manifest với danh sách account row cố định (ví dụ `account_row = 3` ứng với `user_A`).
  2. Trong ngày, file `taikhoan_dat_v2` bị chỉnh sửa (xóa tài khoản ở hàng trước hoặc chèn nick trùng lặp).
  3. `sync-safe-workbook.py` chạy khử trùng / dồn hàng làm thay đổi thứ tự `account_row_index` trong `taikhoan_run_safe.xlsx` (ví dụ vị trí hàng 3 bị dồn sang `user_B`).
  4. Khi runner dispatch `--account-row-index 3`, worker đọc ra `user_B` từ `taikhoan_run_safe.xlsx` nhưng đối chiếu thấy cohort manifest vẫn ghi `user_A`, kích hoạt cơ chế fail-closed.
- **Cách xử lý & Triage:**
  1. Đọc log hoặc summary của máy bị lỗi: `D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/row-X-.../machines/machine_N/.../summary.txt` để lấy `account_row` và `expected_username`.
  2. So sánh entry trong cohort manifest hiện tại (`cron-state/cohorts/YYYY-MM-DD/` hoặc `ACTIVE.json`) với các dòng của máy đó trong `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx`.
  3. Kiểm tra các file ca (`Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`):
     - Ví dụ: Slot 1 (`Tik1`) là nick A, Slot 2 (`Tik2`) là nick B, Slot 3 (`tik3`) là nick C. Nếu trong `taikhoan_dat_v2` slot 2 bị xóa/để trống, `sync-safe-workbook.py` dồn nick C lên hàng 2 (`account_row = 2`) trong `taikhoan_run_safe.xlsx`, trong khi Cohort Manifest vẫn ghi nhận nick C ở Ca 3 (`account_row = 3`).
  4. Chuẩn hóa lại cấu trúc hàng của máy trong `taikhoan_dat_v2_updated .xlsx` (giữ đúng vị trí slot hoặc cập nhật lại manifest đầu ca), sau đó chạy `sync-tik-workbooks.py` và `sync-safe-workbook.py` để đồng bộ nhất quán file safe.
  5. Chạy `compare_tiktok_accounts.py --plan-only` để đảm bảo không còn lỗi `conflicting serials`, sau đó chạy `hermes_taikhoan_sync_cron.py` để cập nhật trạng thái đồng bộ an toàn.

## Bối cảnh & Triage lỗi do Manifest Sync
- **Hiện tượng:** Máy dừng phiên với lỗi digest mismatch hoặc target mismatch khi manifest bị tái tạo giữa ca.
- **Quy tắc chuẩn hóa:** `taikhoan_run_safe.xlsx` là truth duy nhất. Cron sync (`hermes_taikhoan_sync_cron.py`) chỉ đồng bộ 1 chiều từ `taikhoan_dat_v2` sang `taikhoan_run_safe.xlsx`. Không xóa hoặc tái sinh manifest/cohorts trong lúc cron sync chạy.
- **Xử lý khi có lock lỗi:** Dùng `release-device-lock.py` để nhả lock an toàn.



