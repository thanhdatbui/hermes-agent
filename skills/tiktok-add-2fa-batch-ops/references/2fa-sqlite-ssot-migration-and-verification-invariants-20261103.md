# 2FA TikTok Batch Runner: SQLite SSOT Migration & Verification Invariants (03/11/2026)

## 1. Bối Cảnh & Sự Cố Thực Tế
- **Hiện tượng sự cố ban đêm (03/11/2026):** Báo cáo 2FA TikTok toàn farm trả về `Hoàn tất 0 | Lỗi 126` (`POST_SUCCESS_VERIFICATION_FAILED`: 69, `WorkbookError`: 43).
- **Chỉ thị của User:** *"H dùng sqlite r workbook gì nữa"* — Chấm dứt triệt để việc đọc/ghi và hậu kiểm trên file Excel legacy trong runtime farm, quy về duy nhất SQLite SSOT `farm_master.db`.

---

## 2. Các Lỗi Cốt Lõi Khi Nửa Vời Giữa SQLite & Excel
### A. Lỗi `WorkbookError` (43 máy trên cụm Kibe)
- **Căn nguyên:** Hàm `freeze_targets_from_sqlite()` nạp danh sách từ `tiktok_accounts` nhưng:
  1. Thiếu bộ lọc dải máy theo Cluster (`machine <= 80` vs `machine >= 200`), dẫn đến cụm Kibe nạp nhầm máy cụm Admin (rowid 888, 910...). File Excel của Kibe chỉ có ~640 dòng nên văng lỗi tràn dòng.
  2. Dùng `a.rowid` gán cho `source_row` của Excel khiến lệch dòng giữa SQLite và Excel, hàm `_validate_identity()` kiểm tra thấy lệch username lập tức quăng ngoại lệ `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH_USERNAME")`.
- **Giải pháp chuẩn hóa:**
  - Nhận diện cluster dựa trên path hoặc cấu hình:
    - Kibe: `if int(machine) > 80: continue`
    - Admin: `if int(machine) < 200: continue`
  - Bỏ ép đối chiếu dòng Excel: Định danh trực tiếp theo `(username, machine_id)` trong SQLite.

### B. Lỗi `POST_SUCCESS_VERIFICATION_FAILED` (69 máy trên cụm Admin)
- **Căn nguyên:**
  - Hàng trăm tài khoản reg qua Hotmail/SSO đời cũ chưa từng đặt password tĩnh (`password IS NULL`, `blank_pass = True`).
  - Worker con chạy xong đã bật 2FA TOTP thành công trên thiết bị (`status == "success"`).
  - Tuy nhiên hàm `_verification()` lại ép điều kiện:
    ```python
    password_saved = not password_is_blank(...)
    verified = has_2fa and password_saved and journal_purged and released
    ```
  - Khi pass vẫn rỗng, `password_saved` bị đánh giá `False`, biến kết quả thành `failed` với mã `POST_SUCCESS_VERIFICATION_FAILED`.
- **Giải pháp chuẩn hóa:**
  - Hậu kiểm 2FA thành công bắt buộc đọc trực tiếp từ SQLite SSOT `farm_master.db`:
    ```python
    workbook_has_2fa = bool(row and _clean(row["twofa_secret"]))
    password_saved = bool(row and _clean(row["password"])) or target.blank_pass
    ```
  - Trong `run_target`: Công nhận tài khoản hợp lệ nếu đã có 2FA và mật khẩu hợp lệ (hoặc nằm trong diện blank_pass):
    ```python
    password_ok = password_saved or target.blank_pass
    verified = has_2fa and password_ok and journal_purged and released
    ```

### C. Lỗi Crash Khi Thiếu File Excel Legacy Lúc Ghi Credential
- **Căn nguyên:** Trong `core/workbook.py`, hàm `_write_cell()` trước đây bắt buộc gọi `openpyxl.load_workbook()` trước khi cập nhật SQLite. Khi file Excel cũ không còn tồn tại trên đĩa, worker văng `BadZipFile` / `FileNotFoundError` khiến toàn bộ mẻ chạy bị gãy.
- **Giải pháp chuẩn hóa:**
  1. Ghi nhận thẳng vào SQLite SSOT `farm_master.db` trước tiên (`update_tiktok_credentials`).
  2. Thêm guard: `if not path.exists(): return backup`. Nếu không có file Excel legacy, hàm vẫn trả về thành công dựa trên SQLite SSOT.

---

## 3. Quy Tắc Bất Biến Cho Batch Runner Farm
1. **Không nửa nạc nửa mỡ:** Đã chuyển sang SQLite SSOT thì toàn bộ vòng đời: (1) Freeze targets $\rightarrow$ (2) Preflight $\rightarrow$ (3) Ghi nhận $\rightarrow$ (4) Verification sau chạy ĐỀU PHẢI đọc/ghi từ SQLite. Tuyệt đối không để sót bước nào gọi lại file Excel.
2. **Kỷ luật Pipeline:** Sửa file runner của farm bắt buộc kích hoạt qua `python D:/Taadaa/tools/unified_patch_pipeline.py run`. Đối với sửa logic Backend / SQLite không động chạm thiết bị UI, sử dụng `--no-canary` kèm `--no-canary-reason` hợp lệ (`evidence_type=backend`, `requires_screencap=false`).
