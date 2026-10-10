# Hardened Avatar Guard & Override Mechanics (SSOT Patterns)

## 1. Path Resolve & Canonical Traversal Guard
Khi thực hiện `guarded_replace(src, dst, folder, ...)`:
- Luôn gọi `dst = Path(dst_path).resolve()` để triệt tiêu mọi `..`, symlinks hoặc đường dẫn tương đối.
- Bắt buộc kiểm tra canonical parent folder:
  ```python
  folder_str = dst.parent.name
  if folder_str.isdigit():
      path_folder = int(folder_str)
      if path_folder != int(folder):
          raise LockedFolderError(f"Folder mismatch: caller folder={folder} does not match canonical path folder={path_folder}")
  ```
- Điều này ngăn chặn mọi bypass dạng `../<target_folder>/avatar.jpg` khi caller truyền một số folder không tương ứng.

## 2. Tight Grant TTL & Pre-Write Atomic Claim
- **TTL Validation:**
  Khi kiểm tra grant:
  ```python
  created_at = float(data.get("created_at", 0))
  expires_at = float(data.get("expires_at", 0))
  if (expires_at - created_at) > 905 or (expires_at - created_at) < 0:
      return False  # Chặn giả mạo grant có TTL vượt ngưỡng 15 phút (900s)
  ```
- **Pre-Write Atomic Claim & Rollback:**
  1. Claim grant (`consume_grant`) **TRƯỚC** khi thực hiện ghi đè file (`os.replace`). Nếu claim ném lỗi, dừng ngay lập tức mà không đụng chạm tới file gốc.
  2. Hỗ trợ ghi cặp `ROOT_NUOI` + `ROOT_VG`: File grant đã đổi sang `.json.used` lưu danh sách `consumed_targets: list[str]`, cho phép ghi tối đa 2 target khác nhau cho đúng folder trong vòng 60s kể từ thời điểm claim đầu tiên.
  3. Nếu bước ghi đè `os.replace` thất bại (IOError, PermissionError):
     - Nếu lần ghi thứ 2 (VG) thất bại: chỉ gỡ target thứ 2 khỏi `consumed_targets`, **không reset cả grant về unconsumed**.
     - Chỉ khi không còn target nào trong `consumed_targets` mới rollback đổi tên `.used` về lại `.json`.
  4. Ràng buộc paired target nghiêm ngặt: Target bắt buộc phải nằm dưới `ROOT_NUOI` hoặc `ROOT_VG`, tối đa 1 target mỗi root (NUOI + VG), cùng `folder`, và grant/`.json.used` bắt buộc nằm trực tiếp trong `get_grants_dir()`. Nếu parent không phải số trên folder bị khóa -> lập tức ném `LockedFolderError` (fail-closed).

## 3. Exit Code Discipline & Phân Quyền Clarify Trong Parallel Regenerator
- Khi gom kết quả từ `ThreadPoolExecutor`:
  - Bắt exception từ `future.result()` và cộng dồn vào danh sách `failed`.
  - Phân cấp ưu tiên exit code:
    * `failed > 0` -> luôn trả về exit code `1` (kể cả khi có lock conflict).
    * `failed == 0` nhưng `LOCKED_CONFLICTS` xuất hiện -> trả về exit code `3` để báo hiệu `NEEDS_OPERATOR_DECISION`.
- **Kỷ luật Clarify Phân Quyền Khi Gặp Exit Code 3:**
  - Agent **TUYỆT ĐỐI CẤM** tự ý cấp grant hay tự mở khóa ngầm.
  - Agent **BẮT BUỘC DỪNG TIẾN TRÌNH VÀ GỌI `clarify`**:
    * Báo cáo danh sách folder khóa đang trùng ảnh.
    * Đưa 3 lựa chọn (Mặc định: Giữ nguyên khóa; Lựa chọn 2: Cấp One-Time Override Grant cho folder X; Lựa chọn 3: Dừng toàn bộ).
    * **CHỈ KHI OPERATOR CHỌN LỰA CHỌN 2**, hệ thống mới được phép cấp One-Time Grant để ghi đè. Mọi trường hợp khác mặc định giữ nguyên khóa (fail-closed).

