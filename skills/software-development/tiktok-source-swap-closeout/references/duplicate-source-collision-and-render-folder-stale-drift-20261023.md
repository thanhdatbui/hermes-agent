# Duplicate Source Collision & Render Folder Stale Drift Diagnosis (2026-10-23)

## 1. Hiện tượng & Bối cảnh
Khi Operator phát hiện một tài khoản TikTok trên farm (`@stutectzyes` - Máy 1 Tik 8) có biểu hiện bất thường:
- Kênh đăng 9 video nhưng view toàn bộ kẹt ở mức 0–118 view (đáy phân phối thử nghiệm / test floor của TikTok).
- Avatar và tên hiển thị một đằng ("Mai Tít" / avatar thiếu nữ), nhưng video đăng một nẻo (mặt mộc phụ nữ trung niên).
- Nghi vấn của Operator: *"Kênh này chắc chắn cào trùng nguồn video với 1 kênh khác r"*.

## 2. Quy trình đối soát O(1) phát hiện trùng lặp nguồn (Cross-Account Duplicate Proof)

### Bước 1: Tra cứu định danh tài khoản qua Dashboard / SQLite
- Từ `@stutectzyes` tra cứu trong `tiktok_tracker.db` (hoặc qua `/api/data` / `/api/history` của Dashboard):
  + Máy: **1**, Slot Tik: **8** (cụm Kibe).
  + UID: `7685814311604585492`.
  + Trạng thái: Đã đăng 9 video, 4 follower, 19 tim.

### Bước 2: Kiểm tra cấu hình trong Workbook `Tik8.xlsx`
- Hàng Máy 1 trong `Tik8.xlsx` ghi:
  + `Folder Video (Render Đích)`: `8`
  + `Video Goc (Nguồn Cào)`: `561` (Keyword: Mẹ và bé, kênh `@HoiChiLamMe`).
  + `Video Đã Đăng`: `10`.

### Bước 3: Đối soát kho Render `D:/TIKTOK-videonuoinick/8/` vs Kho Nguồn `D:/video goc/`
- Tra cứu metadata video bằng Python OpenCV (không quét đĩa, chỉ đọc đúng file `1.mp4`):
  + File render đang đăng (`D:/TIKTOK-videonuoinick/8/1.mp4`): **171 frames**, 5.7s - 6.0s.
  + File nguồn khai báo (`D:/video goc/561/1.mp4`): **1747 frames**, 58.2s.
  $\rightarrow$ **Phát hiện Stale Render Drift:** Folder render `8` hoàn toàn không được render từ nguồn `561`!

### Bước 4: Truy tìm nguồn gốc thật và va chạm số học (Numeric Overlap Trap)
- Trong hệ thống slot mapping của Taadaa Farm:
  + `Tik8`: Máy 1 có `Folder Video = Máy * 8 = 8`.
  + `Tik1`: Máy 8 có `Video Goc = 8`, `Folder Video = 57`.
- Kiểm tra file nguồn `D:/video goc/8/1.mp4`: Đúng **171 frames**, 5.7s (nguồn cào TikTok `@vunhuongspgiocha`).
- Kiểm tra `kibe/Tik1.xlsx` hàng Máy 8 (`@tolmavhj12k`):
  + `Folder Video`: `57`, `Video Goc`: `8`.
  + Kênh này **đã đăng tới 30 video** từ đúng nguồn `D:/video goc/8/` trước đó!
- **Kết luận:** Folder render `D:/TIKTOK-videonuoinick/8/` chứa tàn dư render từ nguồn `8` cũ (từ đợt 11/09). Khi Máy 1 Tik 8 đăng bài, runner bốc các file này up lên, dẫn đến 2 máy (Máy 1 Tik 8 và Máy 8 Tik 1) đăng cùng một bộ video gốc 171 frames $\rightarrow$ TikTok kích hoạt bộ lọc Multimodal Duplicate bóp sạch view về 0.

## 3. Bài học & Kỷ luật Điều phối (Invariants)

1. **Cấm chỉ nhìn vào `global-ledger` để loại trừ trùng nguồn:**
   - Trong `global-ledger`, kênh `561` (`@HoiChiLamMe`) chỉ bị claim 1 lần duy nhất bởi Máy 1.
   - Nhưng thực tế kênh vẫn bị trùng do **Stale Render Drift** (chưa render đè nguồn mới vào kho render đích).
2. **Kỹ thuật xác minh toán học qua Frame Count O(1):**
   - So sánh trực tiếp `cap.get(cv2.CAP_PROP_FRAME_COUNT)` và `duration` giữa các file `.mp4` ở cả 2 đầu kho. Nếu `fc_render == fc_raw_other != fc_raw_target`, đó là bằng chứng không thể chối cãi của việc đăng nhầm nguồn.
3. **Quy chuẩn dọn sạch khi đổi nguồn (Wipe & Rebuild):**
   - BẮT BUỘC xóa sạch cả kho render (`D:/TIKTOK-videonuoinick/<F>`) về 0 file trước khi render đợt mới.
   - Khóa cứng `Video Goc = Folder Video = <F>` để tránh va chạm chéo giữa công thức `F_src` và `F_vid`.
   - Bảo lưu con trỏ `Video Đã Đăng` để dải render mới bắt đầu từ `(Video Đã Đăng + 1).mp4`.
