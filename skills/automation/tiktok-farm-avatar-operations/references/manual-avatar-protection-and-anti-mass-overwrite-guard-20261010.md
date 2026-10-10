# Manual Avatar Protection & Anti-Mass-Overwrite Guard (2026-10-10)

## Problem & Incident Context
- **Sự cố:** Kênh `@huy010822` (Máy 18 Tik 5, folder 141) trước đó đã được Operator yêu cầu đổi avatar bằng tay về hình nam sinh khăn quàng đỏ (video `4.mp4` @ 15s). Tuy nhiên, sau đó tiến trình quét đĩa tái tạo avatar hàng loạt (`regenerate_unique_avatars.py`) chạy để khử trùng lặp cho các acc khác trên farm đã quét trúng folder 141, gọi `_make_avatar.py 141`, sinh ra frame hoạt hình tháp ("FREQUENT WIND DI TẢN LỚN") và đè lên `avatar.jpg`, sau đó watchdog ca tối upload đè lên điện thoại làm hỏng avatar thủ công của Operator.
- **Chỉ thị dứt khoát của Operator:** *"Từ h bất kì kênh nào t yêu cầu đổi ava = tay thì k đc script can thiệp nữa (hiện có code kiểu quét folder tạo ava lại hàng loạt, nó dùng fix mấy nick lúc trc, nhưng vô tình phá luôn nick t yêu cầu đổi = tay t chat vs m)"*.

## Architecture Solution (3 Tầng Bảo Vệ)

### 1. In-Folder Lock Marker (`.manual_avatar_locked`)
- Bất kỳ folder nào được Operator yêu cầu đổi avatar bằng tay, BẮT BUỘC tạo file marker nguyên tử:
  * `D:/TIKTOK-videonuoinick/<folder>/.manual_avatar_locked`
  * `D:/video goc/<folder>/.manual_avatar_locked`
- Nội dung JSON ghi nhận metadata:
  ```json
  {
    "protected": true,
    "folder": 141,
    "video_goc": 338,
    "username": "huy010822",
    "machine": 18,
    "tik": 5,
    "reason": "Operator manual avatar request via chat",
    "locked_at": "YYYY-MM-DD HH:MM:SS"
  }
  ```

### 2. Central Registry SSOT
- Ghi nhận danh sách folder bảo vệ tập trung tại:
  * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
  * `D:/Taadaa/data/manual_avatar_protected_folders.json`
- Schema:
  ```json
  {
    "protected_folders": [141, 338, 2, 148, 266, 275, 398, 138],
    "accounts": {
      "141": {"username": "huy010822", "machine": 18, "tik": 5, "description": "Hài học đường nam sinh khăn quàng đỏ"}
    }
  }
  ```

### 3. Guard Module & Preflight Interceptor (`manual_avatar_guard.py`)
- Module `D:/Taadaa/Tiktok-video/scripts/manual_avatar_guard.py` cung cấp 2 hàm SSOT:
  * `get_protected_folders() -> set[int]`: Đọc từ cả central JSON và quét in-folder marker.
  * `is_folder_avatar_protected(folder) -> bool`: Kiểm tra O(1) folder có được bảo vệ thủ công không.

### 4. Chốt chặn trong các Script Hàng Loạt
- **`regenerate_unique_avatars.py`:**
  * Trong `find_all_duplicate_folders()`: Loại trừ tuyệt đối `protected_folders` khỏi `to_regen` (`to_regen = to_regen - protected`).
  * Trong `process_folder(folder)`: Kiểm tra `is_folder_avatar_protected(folder)` ngay đầu hàm; nếu True trả về `(folder, True, "SKIPPED_MANUAL_PROTECTED", 0.0)` mà KHÔNG gọi `_make_avatar.py` và KHÔNG ghi đè file.
- **`_make_avatar.py`:**
  * Bổ sung cờ `--force`.
  * Nếu không có `--force` và folder nằm trong danh sách bảo vệ: in log `[GUARD]` và return 0 thoát sạch sẽ.
- **Unit test xác minh:**
  * `tests/test_manual_avatar_guard.py` kiểm tra cả việc nhận diện folder bảo vệ và hàm `process_folder` bỏ qua an toàn.
