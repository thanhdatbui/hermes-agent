# State.db CodexRuntime Paths & Pre-Sept 11 Historical Source Triage (2026-10-09)

## Context & Operator Question
Khi kênh bị lệch ngách (ví dụ đang đăng gái bỗng chuyển sang tai nạn giao thông), Operator hỏi:
*"Lấy lại kênh cũ đăng đc k"* và *"Chứ kênh cũ tải có lưu ở file db hay gì đó chứ???"*

## 1. Cạm Bẫy 0-Byte `state.db` Placeholders
Trong các repo và thư mục dữ liệu Taadaa, tồn tại nhiều file `state.db` rỗng (0 bytes):
- `D:\Taadaa\Tiktok-video\state.db` (0 KB)
- `D:\Taadaa\data\state.db` (0 KB)
- `D:\OneDrive\SharedData\tiktok-video\state.db` (0 KB)
- `D:\Taadaa\data\tiktok_accounts.db` (0 KB)

Nếu Coordinator truy vấn các file trên, SQLite trả về `tables: []`, dễ gây ngộ nhận là hệ thống không lưu vết lịch sử tải kênh!

## 2. Đường Dẫn Ground Truth Của `state.db`
Cơ sở dữ liệu lưu trữ metadata tải video thực tế (>57.000 video) nằm tại:
- **`C:\CodexRuntime\tiktok-video\state.db`** (~34 MB) — chứa bảng `folders` (640 hàng) và `videos` (>57.600 hàng với `source_channel`, `uploader`, `source_url`, `status`).
- **`D:\CodexRuntime\tiktok-video\state.db`** (~23 MB) — bản sao lưu / worker runtime trên ổ D.
- **`D:\OneDrive\SharedData\tiktok-video\global-ledger\*.jsonl`** — nhật ký phân tán claim và download theo từng máy (`Admin.jsonl`, `Kibe.jsonl`).

## 3. Ranh Giới Lịch Sử Trước và Sau 11/09/2026 (Migration Drift)
- **Trước 11/09/2026:**
  - Các tài khoản đăng ký cuối tháng 8/2026 (như đợt 25/08) tải video theo batch thủ công / pipeline sơ khởi.
  - Lịch sử tải của đợt này chưa được nạp vào bảng `folders` chuẩn hóa của `state.db`.
- **Từ 11/09/2026 đến 14/09/2026:**
  - Hệ thống triển khai đợt chuẩn hóa 640 folders (`download_by_niche.py`).
  - Các folder từ 480 đến 640 được nạp các kênh mới (ví dụ Folder 496 được gán cho `@Cameragiaothong` ngày 11/09/2026; Folder 622 được gán cho `ToyStation` ngày 14/09/2026).
  - Thao tác này ghi đè bản ghi mới vào `folders` và `videos` trong `state.db`, khiến thông tin kênh cũ của các acc reg từ tháng 8 không còn xuất hiện trong bảng `folders`.

## 4. Quy Trình Trả Lời và Đối Soát Ground Truth Khi Operator Hỏi Về DB
1. **Kiểm tra đúng file DB:** Luôn kết nối vào `C:\CodexRuntime\tiktok-video\state.db` và `global-ledger/*.jsonl`. Tuyệt đối không tra vào file 0-byte.
2. **Đối soát mốc thời gian:**
   - Đọc ngày tạo acc (`taikhoan_dat_v2_updated .xlsx` cột `Ngày Tạo` hoặc `snapshots.created_at`).
   - Đọc `created_at` trong `folders` của `state.db` cho số folder đó.
   - Nếu `created_at` trong DB muộn hơn ngày tạo acc (ví dụ acc tạo 25/08 nhưng folder tạo 11/09), giải thích ngay cơ chế chuẩn hóa đè folder 11/09 đã ghi đè bản ghi cũ.
3. **Phương án khôi phục kênh cũ:**
   - Dùng chi tiết nhận diện trực quan từ ảnh Profile (caption thumbnail, nhân vật, bối cảnh) để truy tìm kênh hoặc đề xuất kênh thay thế cùng vibe trong kho 12 Niche Hot.
   - Reset `Video Đã Đăng` về đúng mốc trước khi bị đăng đè (ví dụ mốc 5 clip cũ) để tiếp tục duy trì nhận diện và tệp khán giả của kênh.
