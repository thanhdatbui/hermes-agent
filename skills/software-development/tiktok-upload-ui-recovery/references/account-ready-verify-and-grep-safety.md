# Account Ready Verify & Batch Failure Symptom Extraction

## 1. Pitfall: `tap_profile()` bị guard `is_profile_root` chặn khi verify account (`ACCOUNT_VERIFY_MISMATCH`)
- **Hiện tượng:** Sau khi chọn account trong Switcher, màn hình Profile chưa load kịp username mới hoặc đang hiển thị profile cũ. State machine trong `_handle_account_ready` gọi `tap_profile()` trong vòng lặp retry 20s để làm mới tab Hồ sơ, nhưng `tap_profile()` có guard `if self.is_profile_root(xml_text): return` dẫn tới từ chối tap, làm vòng lặp verify bị timeout và fail `ACCOUNT_VERIFY_MISMATCH` -> `upload_subprocess_nonzero`.
- **Nguyên nhân:** `is_profile_root(xml_text)` đánh giá dựa trên sự xuất hiện của các nút profile ("Sửa hồ sơ", "Thêm tiểu sử",...). Màn hình đang ở Profile (của nick cũ) nên hàm trả về `True`, khiến `tap_profile()` coi là "đã ở Profile" và bỏ qua lệnh tap.
- **Xử lý chuẩn:**
  1. Thêm tham số `force: bool = False` cho `adapter.tap_profile(force: bool = False)`:
     ```python
     if not force and self.is_profile_root(xml_text):
         logger.info("[TAP_PROFILE] Profile root already visible; skip duplicate tap")
         return
     ```
  2. Trong `_handle_account_ready` của `state_machine.py`, khi verify account bị mismatch và cần re-tap, gọi `self.context.adapter.tap_profile(force=True)`.
  3. Cập nhật `run_tiktok_upload_batch.ps1` để đọc `report.reason` / `last_state` từ `report.json` và hiển thị trực tiếp lên console/summary thay vì nhãn thô `upload_subprocess_nonzero`.

## 2. Anti-Pattern: Unindexed Broad Grep / Disk Scan
- **Hiện tượng:** Chạy lệnh `grep -rn` hoặc search trên các cây thư mục lớn (`D:/Taadaa/`, `D:/OneDrive/`, `C:/Users/Kibe/`) mà không chỉ định phạm vi file hẹp.
- **Hậu quả:** Terminal timeout (900s), tiến trình treo ngầm và block main loop của Hermes cho tới khi nhận lệnh can thiệp.
- **Quy tắc:**
  - BẮT BUỘC dùng `python D:/Taadaa/tools/inspect_machine.py <N>` khi nhận alert máy.
  - Khi cần tìm file code, chỉ định chính xác đường dẫn file hoặc thư mục lá hẹp (ví dụ `scripts/tiktok_workflow/*.py`). Tuyệt đối không grep recursive từ root `D:/Taadaa/` hay `D:/OneDrive/`.
