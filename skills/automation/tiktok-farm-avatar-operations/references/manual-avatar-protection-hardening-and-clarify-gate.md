# Manual Avatar Protection Hardening & Clarify Gate Protocol (2026-10-10)

## 1. Bối cảnh & Căn nguyên Lỗi Hệ thống
- **Hiện tượng thực tế:** Trong các đợt chạy script quét tái sinh avatar hàng loạt toàn farm (`regenerate_unique_avatars.py`), script phát hiện các nhóm avatar trùng mã băm MD5 hoặc folder thiếu avatar. Thuật toán tự động cắt lại frame mới đè lên `avatar.jpg`, rồi UPDATE `avatar_replace_queue` về `status = 'PENDING'`.
- **Hậu quả nghiêm trọng:** Các tài khoản mà Operator đã dày công chỉnh tay hoặc chọn avatar chuẩn qua chat bị script tự động xóa đè mất, thay bằng một avatar tự động bị lỗi (cắt lẹm, dính banner, hoặc sai nhân khẩu học), buộc Operator phải phát cáu: *"Có mấy lần t cho script tạo lại ava ấy... xong nó cứ đi tạo lại máy t đã yêu cầu chỉnh tay... phá luôn nick t yêu cầu đổi = tay"*.
- **Quy chuẩn bắt buộc:** Khi Operator yêu cầu can thiệp đổi avatar cho bất kỳ nick nào qua chat, hệ thống **PHẢI TỰ ĐỘNG KHÓA VĨNH VIỄN NGAY LẬP TỨC**. Tuyệt đối không được đợi Operator phải nhắc mới khóa.

---

## 2. 5 Nguyên Tắc Bất Biến (Invariant Architecture)

1. **Mặc định là KHÓA (Fail-Closed tuyệt đối):**
   - Mọi tình huống bất thường (registry JSON lỗi cú pháp, ổ đĩa chưa mount, folder ID không parse được) đều được xem là **ĐANG BỊ KHÓA** hoặc **DỪNG CHẠY NGAY LẬP TỨC** (`GuardIntegrityError`), tuyệt đối không coi là "không khóa" (chấm dứt lỗ hổng fail-open `except Exception: pass`).
2. **Quyền mở khóa thuộc ĐỘC QUYỀN Operator:**
   - Script không được tự mở khóa, Agent cũng không. Bất kỳ hành vi tự ý mở khóa ngầm hay xóa cờ bảo vệ đều bị coi là vi phạm nghiêm trọng.
3. **Mở khóa là One-Time Override Grant, KHÔNG PHẢI XÓA KHÓA:**
   - Mở khóa KHÔNG PHẢI là xóa folder khỏi `manual_avatar_protected_folders.json` hay xóa `.manual_avatar_locked`.
   - Khi Operator cho phép mở khóa, hệ thống chỉ cấp một `One-Time Override Grant` (thời hạn 15 phút, dùng đúng 1 lần cho đúng folder được duyệt). Sau khi ghi ảnh mới xong, **trạng thái khóa vẫn còn nguyên vẹn**.
4. **Điểm Ghi Duy Nhất (`guarded_replace`):**
   - Mọi thao tác ghi đè lên file `avatar.jpg` trên toàn farm bắt buộc phải đi qua hàm chốt chặn `guarded_replace()`. CẤM các script tự ý gọi `os.replace` trần.
   - Khi có grant hợp lệ, `guarded_replace` tự động sao lưu ảnh cũ vào `.manual_backup/avatar.<timestamp>.jpg` trước khi thay thế.
5. **Quyền Không Kế Thừa:**
   - Quyền cấp cho một lần chạy không có giá trị cho các lần chạy sau. Quyền này cấm lưu vào memory agent để tự suy diễn.

---

## 3. Bộ Chốt Chặn Code (G1-G7 & R1-R5)

### Module `manual_avatar_guard.py`:
- **G1 (Fail-Closed Loader):** `get_protected_folders()` ném `GuardIntegrityError` nếu registry JSON bị hỏng.
- **G2 (Registry Integrity):** `validate_registry_integrity()` kiểm tra tính hợp lệ và cấu trúc của `manual_avatar_protected_folders.json`.
- **G3 (Lock Info Introspection):** `get_lock_info(folder)` trả về thông tin chi tiết: `{folder, locked, sources, account_info}` để nạp vào prompt `clarify`.
- **G4 (Guarded Atomic Replace):** `guarded_replace(src, dst, folder, caller, grant_path=None)`:
  * Nếu folder bị khóa và không có grant hợp lệ $\to$ ném `LockedFolderError`.
  * Nếu có grant hợp lệ $\to$ sao lưu ảnh cũ, `os.replace`, và gọi `consume_grant`.
- **G5 (Override Grant API):**
  * `issue_override_grant(folder, reason, ttl_seconds=900)`: Ghi file JSON grant (used: False, expires_at).
  * `verify_override_grant(grant_path, folder)`: Kiểm tra file tồn tại, đúng folder, chưa hết hạn, `used == False`.
  * `consume_grant(grant_path)`: Đánh dấu `used: True`.

### Module `regenerate_unique_avatars.py`:
- **R1:** Gọi `validate_registry_integrity()` ngay đầu `main()`, exit 1 nếu hỏng.
- **R2:** Quét phát hiện `locked_hits = unique_folders & protected`. Báo cáo danh sách các folder trùng bị khóa.
- **R3:** Toàn bộ lệnh thay thế file đều gọi qua `guarded_replace(tmp, final, folder=folder, caller="regenerate_unique_avatars")`.
- **R4:** Nếu phát hiện `locked_hits`, xuất khối JSON `[LOCK_CONFLICT]` và trả về mã thoát **Exit Code 3 (`NEEDS_OPERATOR_DECISION`)**.
- **R5:** CẤM tuyệt đối các cờ bypass như `--force`, `--unlock`, `--ignore-lock`.

---

## 4. Giao Thức Điều Phối Clarify Gate (Human-In-The-Loop)

Khi script quét tái sinh avatar hàng loạt gặp folder bị khóa và trả về Exit Code 3 kèm `LOCK_CONFLICT`:
1. **Agent BẮT BUỘC DỪNG TIẾN TRÌNH TÁI SINH VÀ GỌI TOOL `clarify`:**
   - CẤM tự ý mở khóa ngầm.
   - CẤM hỏi bằng text chat suông trôi nổi; phải dùng đúng tool `clarify` có selectable options.
2. **Cấu trúc câu hỏi `clarify` chuẩn:**
   - **Question:** *"Quét hàng loạt phát hiện [N] folder đang bị khóa thủ công nhưng dính mã trùng/lỗi: Folder [X] (Nick @..., Máy M, Tik T). Bạn có muốn mở khóa để tạo lại avatar tự động không?"*
   - **Choices:**
     1. `Bỏ qua tất cả, giữ nguyên avatar thủ công (Khuyên dùng)`
     2. `Mở khóa và tạo lại riêng cho Folder [X]`
     3. `Dừng toàn bộ tiến trình quét`
3. **Quy tắc xử lý câu trả lời:**
   - **CHỈ KHI Operator chọn Lựa chọn 2:** Agent mới gọi `issue_override_grant(X, reason="Operator approved via clarify")` và chạy lại tái sinh cho đúng folder X với `--override-grant <file>`.
   - **Nếu Operator không phản hồi hoặc trả lời mơ hồ:** Mặc định 100% LUÔN LÀ **LỰA CHỌN 1 (BỎ QUA GIỮ NGUYÊN)**.
