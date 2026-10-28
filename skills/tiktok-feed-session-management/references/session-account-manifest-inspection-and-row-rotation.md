# Session Account Manifest Inspection & Farm Row Rotation Verification

## 1. Farm Row Schedule & Rotation Logic
- **Ca 1 (Sáng: 06:00 - 12:00, gồm 2 phiên 06:00 và 08:00):**
  - **Ngày lẻ (Odd dates - 25, 27, 29, 31, 01...):** Ưu tiên chạy **Row 1** (Tik 1). Có thể kèm máy bù/thay thế thuộc Row khác nếu máy đó thiếu nick Row 1.
  - **Ngày chẵn (Even dates - 26, 28, 30, 02...):** Tự động xoay sang ưu tiên **Row 2** (Tik 2).
  - Tỷ lệ trùng nick (overlap) giữa 2 ca sáng của ngày lẻ và ngày chẵn kế tiếp là **0%** (hoàn toàn khác biệt).
- **Ca 2 (Chiều), Ca 3 (Tối), Ca 4 (Đêm):** Luân phiên cuốn chiếu theo ma trận phân bổ tài khoản (các row 3-8).

## 2. O(1) Manifest Inspection (Chống quét đĩa diện rộng)
Khi User hỏi đối soát tài khoản của ca hiện tại so với hôm qua hoặc ca trước:
- **CẤM TUYỆT ĐỐI:** Dùng `search_files` quét diện rộng hay `os.walk` từ thư mục gốc `D:/Taadaa/runtime`.
- **ĐƯỜNG DẪN CHUẨN XÁC O(1):**
  `D:/Taadaa/runtime/<cluster>/live/<YYYY-MM-DD>/<run_id>/<timestamp>/run_manifest.json`
  - `<cluster>`: `kibe` (máy 1-80) hoặc `admin` (máy 201-280).
  - `<run_id>`: Tên run dạng `row-0-060049`, `row-0-080046`, v.v. (trích từ log watchdog).
  - `<timestamp>`: Thư mục con dạng `YYYYMMDD-HHMMSS` duy nhất bên trong `<run_id>`.

## 3. Cấu trúc `run_manifest.json` & Trường dữ liệu cốt lõi
- **Trường `multi_machine_summary` (list dict):**
  Mỗi phần tử chứa thông tin máy đã chạy:
  ```json
  {
    "machine": 1,
    "expected_username": "account:2e9444e799",
    "account_row": 2,
    "account_row_index": 2,
    "final_status": "success",
    "stop_reason": "None",
    "swipes_completed": 120
  }
  ```
- **Cách trích xuất nhanh kiểm chứng Overlap:**
  Đọc `multi_machine_summary`, tạo dict `{machine: (expected_username, account_row)}`.
  So khớp giao tập `set(accs_today.values()) & set(accs_yesterday.values())`.
  Nếu `len(overlap) == 0`: Khẳng định 100% nick chạy hôm nay đã được đảo khác hoàn toàn hôm qua.
