# Vấn Đề CRLF Anchor & Multi-File Guard Khi Dispatch Avatar Task

## 1. Hiện Tượng & Cạm Bẫy Khi Điều Phối Task Avatar
Khi Coordinator điều phối sửa đổi các file đăng ký bảo vệ avatar (`manual_avatar_protected_folders.json`) hoặc cấu hình Excel/DB qua `delegate_task`:

1. **Lỗi `ANCHOR_NOT_FOUND` do CRLF (`\r\n`) trên Windows**:
   - File JSON hoặc script trên Windows thường lưu bằng định dạng dòng `CRLF` (`\r\n`).
   - Nếu trong `OLD_STRING: <<< ... >>>` của `delegate_task`, Coordinator copy chuỗi nhiều dòng từ terminal hoặc string literal có `LF` (`\n`), bộ kiểm tra contract của Guard sẽ đối soát chuỗi thô và báo lỗi `ANCHOR_NOT_FOUND` mặc dù mắt thường thấy giống hệt.
   - **Cách xử lý**:
     * Tránh anchor nhiều dòng phức tạp khi file có CRLF.
     * Sử dụng anchor 1 dòng duy nhất có định danh độc nhất (ví dụ: một dòng ID/folder cụ thể) hoặc chuẩn hóa bằng script python focused.

2. **Lỗi `MULTI_FILE_VIOLATION`**:
   - Guard Taadaa siết chặt: Tối đa $\le 2$ files trong 1 task delegation (1 file nghiệp vụ + 1 file test).
   - Khi cần cập nhật đồng bộ nhiều nơi (`manual_avatar_protected_folders.json` ở cả 2 repo `data/` và `Tiktok-video/data/`, `Tik<N>.xlsx`, SQLite `tiktok_tracker.db`):
     * CẤM gộp tất cả 4-5 files vào 1 task `delegate_task`.
     * Bắt buộc phân rã theo ngữ nghĩa: 1 task chuyên cho registry SSOT, 1 task cho Excel/DB, hoặc sử dụng runner script chuẩn có sẵn trên farm.

3. **Lỗi `PATH_NOT_ABSOLUTE` do dấu gạch chéo ngược Windows (`\`)**:
   - Khi bọc path trong `FILE: <<< ... >>>`, nếu dùng `\` (ví dụ `D:\Taadaa\data\...`), parser guard có thể diễn giải sai hoặc báo `PATH_NOT_ABSOLUTE`.
   - **Quy tắc**: Luôn chuẩn hóa đường dẫn tuyệt đối với dấu gạch chéo xuôi (`/`), ví dụ: `FILE: <<< D:/Taadaa/data/manual_avatar_protected_folders.json >>>`.

4. **Kỷ Luật Ngân Sách Diff (`DIFF_BUDGET_EXCEEDED`) & Định Dạng Focused Test**:
   - **Ngân sách O(1) cứng**: `NEW_STRING` trong task `EDIT` bắt buộc $\le 30$ dòng code thay đổi. Nếu vượt quá, guard sẽ từ chối ngay lập tức (`DIFF_BUDGET_EXCEEDED`). Phải viết code súc tích, cô đọng các bước import và logic thực thi.
   - **Chuẩn hóa `FOCUSED_TEST`**: Guard chỉ chấp nhận 2 định dạng:
     * `python -m py_compile <file_path>` (cho syntax/integrity checks).
     * `python -m pytest <file_path>::<test_node> -q` (cho logic test).
     * Các lệnh tự do như `python script.py --verify` sẽ bị guard chặn với lỗi `INVALID_FOCUSED_TEST_FORMAT`.
   - **Cấm `subprocess` trong `python -c` của Coordinator**: Lệnh `python -c` ở phiên chính chỉ dùng đọc dữ liệu read-only. Gọi `subprocess` trong `python -c` bị chặn ngay. Các tác vụ can thiệp hệ thống phức tạp hoặc vượt ngân sách T1 (5 files, 200 dòng) bắt buộc dispatch Worker.

5. **Cạm Bẫy Cạn Kiệt Ngân Sách T1 Coordinator Khi Xử Lý Lô Nhiều Nick (Multi-Account T1 Exhaustion)**:
   - **Hiện tượng**: Khi nhận yêu cầu xử lý avatar cho nhiều nick cùng lúc (ví dụ lô 3 nick), Coordinator tự viết liên tiếp các script trích xuất frame, lọc khuôn mặt, tạo preview bằng `write_file`.
   - **Hậu quả**: Chạm trần ngân sách tích lũy của Coordinator: `⛔ [COORDINATOR WRITE DENIED]: Hết ngân sách T1 (tối đa 5 files, <= 200 dòng cộng dồn cả session)`. Coordinator bị khóa quyền ghi file trong toàn bộ phần còn lại của session.
   - **Kỷ luật điều phối bắt buộc**:
     * Coordinator CHỈ tra cứu định danh, đọc mapping Excel/DB read-only O(1) trong phiên chính.
     * CẤM TUYỆT ĐỐI tự tạo chuỗi 3–4 script xử lý ảnh trực tiếp trong session Coordinator.
     * BẮT BUỘC dispatch Worker subagent ngay từ đầu qua `delegate_task` với `TASK_KIND: CREATE`, `FILE: D:/Taadaa/reports/<script>.py`, và `FOCUSED_TEST: python -m py_compile D:/Taadaa/reports/<script>.py` để Worker viết code và tự thực thi trích xuất/crop ảnh.
   - **Bẫy `lifecycle_guard.py` với lệnh terminal inline**:
     * Lệnh Python inline (`python -c "..."`) nhiều dòng phức tạp chứa escape nháy, ký tự đặc biệt hoặc đường dẫn lồng nhau dễ khiến `lifecycle_guard.py` gặp lỗi `ValueError: open: embedded null character in path` hoặc kích hoạt `GUARD_DANGEROUS_ROOT`.
     * Luôn giữ lệnh terminal ngắn gọn hoặc giao Worker viết file script chuyên dụng để chạy.

## 2. Quy Trình Chẩn Đoán Lệch Niche & Avatar Từ Ảnh Người Dùng Cung Cấp
Khi User gửi ảnh chụp màn hình kênh TikTok và yêu cầu "Đổi ava nick này":
1. **Trích xuất định danh kênh O(1)**:
   - Đọc Display Name và Handle (`@username`) từ ảnh (qua OCR hoặc Vision).
   - Truy vấn SQLite `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping`):
     ```sql
     SELECT username, may, tik FROM account_mapping WHERE username LIKE '%...%';
     ```
2. **Tính toán đối soát $F_{src}$ và $F_{out}$**:
   - Tính $F_{src} = (Tik - 1) \times 80 + Máy$.
   - Đọc dòng máy trong `Tik<Tik>.xlsx` để lấy $F_{out}$ (`Folder Video`), `video gốc`, `Keyword Video`, `Avatar`.
3. **Phát hiện Drift (Lệch Niche & Lệch Avatar)**:
   - So sánh nội dung video trên kênh (từ thumbnail/tiêu đề trong ảnh) với `Keyword Video` trong Excel.
   - Kiểm tra xem $F_{src}$ hay $F_{out}$ đang chứa video trùng khớp với kênh.
   - Kiểm tra trạng thái máy qua `python D:/Taadaa/tools/inspect_machine.py <M>`. Nếu thiết bị offline, báo cáo rõ hiện trường phần cứng (cáp USB/nguồn) song song với việc chuẩn bị sẵn avatar đạt chuẩn $cy \approx 0.2 \times H$.
