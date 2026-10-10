# Manual Avatar Protection Hardening & Autonomous Review Loop (2026-10-10)

## 1. Bối cảnh & Sự cố Ghi Đè Avatar Chỉnh Tay
- **Hiện tượng:** Khi Operator yêu cầu chỉnh tay avatar cho một nick lẻ (như `@trn.m.m620`), sau khi upload xong thì vài ngày sau chạy script quét hàng loạt tái sinh avatar (`regenerate_unique_avatars.py`) lại tự ý cắt frame mới đè lên `avatar.jpg`, reset database queue về `PENDING`, và watchdog upload đè ảnh lỗi lên thiết bị.
- **Yêu cầu của Operator:**
  1. Bất kỳ nick nào Operator đã yêu cầu đổi/chọn avatar thủ công qua chat: Hệ thống **BẮT BUỘC TỰ ĐỘNG KHÓA VĨNH VIỄN** (ghi registry và cắm marker `.manual_avatar_locked`), cấm chờ Operator phải nhắc.
  2. Khi chạy script quét tái tạo hàng loạt, gặp folder bị khóa: **CẤM TUYỆT ĐỐI tự ý mở khóa hay đè ảnh**. Bắt buộc dừng lại hỏi Operator qua tool `clarify`, chỉ khi Operator phê duyệt rõ ràng mới được cấp quyền One-Time Override Grant.
  3. Khi Operator ra lệnh "làm đến khi Claude review duyệt", Coordinator **BẮT BUỘC tự động loop remediation** cho đến khi đạt APPROVED (>=85/100), cấm dừng lại ở Strike 1 hỏi xin phép tiếp tục.

---

## 2. Kiến Trúc 5 Nguyên Tắc Bất Biến (Invariant Rules)
1. **Mặc định là KHÓA (Fail-Closed tuyệt đối):**
   - Registry JSON hỏng hoặc mất file -> ném `GuardIntegrityError`, cấm trả về set rỗng.
   - Folder identifier không parse được thành số nguyên (`"abc"`, `None`) -> `is_folder_avatar_protected` mặc định trả về `True` (bị khóa).
2. **Quyền mở khóa thuộc ĐỘC QUYỀN của Operator:**
   - Script và Agent tuyệt đối cấm tự ý mở khóa hoặc tự cấp grant.
3. **Mở khóa là One-Time Override Grant, KHÔNG PHẢI XÓA KHÓA:**
   - Cấm xóa file registry và cấm xóa marker `.manual_avatar_locked`.
   - Grant chỉ có giá trị cho đúng folder đó, có nonce ngẫu nhiên, TTL tối đa 900s, và bị đổi tên nguyên tử thành `.json.used` khi claim. Khóa gốc vẫn còn nguyên vẹn sau khi ghi.
4. **Điểm Ghi Duy Nhất (`guarded_replace`):**
   - Mọi thao tác ghi/đổi `avatar.jpg` phải đi qua `guarded_replace()`.
   - Hàm tự động kiểm tra chéo số folder trích xuất từ `dst_path.parent.name`; nếu caller truyền sai folder để lách guard -> ném `LockedFolderError`.
   - Hỗ trợ cặp ghi NUOI + VG bằng cờ `consume=False` ở lần 1 (NUOI) và `consume=True` ở lần 2 (VG) để 1 grant hoàn tất cả 2 thư mục nguyên tử.
5. **Quyền Không Kế Thừa:**
   - Quyền grant chỉ dùng 1 lần trong phiên; cấm ghi nhớ quyền vào memory để tự suy diễn ở các phiên sau.

---

## 3. Chốt Chặn Code G1-G7 & R1-R5

### Trong `manual_avatar_guard.py`:
- **G1 (Fail-Closed):** Ném `GuardIntegrityError` khi mất registry, corrupt JSON, hoặc marker scan lỗi. `is_folder_avatar_protected` fail-closed trả `True` cho input rác.
- **G2 (Đối soát kép):** `validate_registry_integrity()` so khớp `set(folders1) == set(folders2)` giữa 2 file registry; trả về `False` nếu có sự sai lệch.
- **G4 (Ràng buộc Path):** `guarded_replace()` tự parse `path_folder = int(dst_path.parent.name)`; nếu `path_folder != folder` -> ném `LockedFolderError`. Tự động sao lưu ảnh cũ vào `.manual_backup/avatar.<timestamp>.jpg` trước khi ghi đè.
- **G5 (Thắt chặt Grant):**
  * `issue_override_grant(folder, reason, ttl_seconds)`: TTL cứng $\le 900\text{s}$, sinh nonce ngẫu nhiên 6-byte hex, lưu trong `get_grants_dir()`.
  * `verify_override_grant(grant_path, folder)`: Kiểm tra file nằm trong `get_grants_dir()`, chưa có đuôi `.used`, còn hạn TTL.
  * `consume_grant(grant_path)`: Đổi tên nguyên tử sang `.json.used` qua `os.replace`. Nếu file thiếu hoặc đã đổi tên -> ném `LockedFolderError`.
- **G6 (Xóa cờ bypass):** Xóa bỏ hoàn toàn cờ `--force` khỏi `_make_avatar.py`.

### Trong `regenerate_unique_avatars.py`:
- **R1:** Kiểm tra toàn vẹn lúc khởi động qua `validate_registry_integrity()`, dừng ngay nếu fail.
- **R2:** Gom các folder bị trùng có khóa vào danh sách `LOCKED_CONFLICTS`.
- **R3 (Exit Code 3):** Khi hoàn tất quét nếu phát hiện `LOCKED_CONFLICTS`:
  * Xuất khối JSON `[LOCK_CONFLICT]`.
  * Thoát với **`sys.exit(3)`** (`NEEDS_OPERATOR_DECISION`) để Agent nhận diện trạng thái cần can thiệp.

---

## 4. Quy Trình Hỏi - Đáp Clarify & Tự Động Remediation
1. **Khi script quét trả về Exit Code 3 (`LOCK_CONFLICT`):**
   - Agent **BẮT BUỘC DỪNG LẠI VÀ GỌI TOOL `clarify`**:
     * Báo cáo danh sách folder khóa đang bị trùng.
     * Option 1 (Mặc định): Bỏ qua tất cả, giữ nguyên avatar thủ công.
     * Option 2: Mở khóa và tạo lại riêng cho Folder [X] (cấp One-Time Grant).
     * Option 3: Dừng toàn bộ tiến trình quét.
   - **Quy tắc Fail-closed:** Không phản hồi hoặc hết giờ -> Mặc định LUÔN LÀ OPTION 1 (Bỏ qua giữ nguyên).
2. **Kỷ luật Điều phối khi có Lệnh "Làm đến khi Claude Review Duyệt":**
   - Khi Operator giao task kèm lệnh review/chốt phiên: Coordinator **CẤM TUYỆT ĐỐI** dừng lại ở Strike 1 (khi reviewer trả về REJECTED) để hỏi xin phép "có muốn làm tiếp không".
   - BẮT BUỘC tự động đọc kỹ các finding của reviewer, cập nhật Patch Contract O(1), dispatch worker khắc phục triệt để, chạy test 100% pass, và tái kích hoạt review cho đến khi nhận **VERDICT: APPROVED ($\ge 85/100$)**.
