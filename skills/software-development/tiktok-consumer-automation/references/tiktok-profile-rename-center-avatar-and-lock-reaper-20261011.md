# TikTok Profile Rename Flow, Center-Avatar Layout & Dead-Lock Recovery (2026-10-11)

## 1. Kỷ Luật Chống Re-invent Code Đổi Tên
- **Cảnh báo từ User:** *"là sao ngày nào t cũng đổi tên mà cứ đi viết lại code đổi tên chi v"*
- **CẤM TUYỆT ĐỐI:** Tự ý nhân bản script riêng lẻ dạng `do_rename_m<ID>.py` (m8, m20, m44, m46, m71, m76...) khi nhận task đổi tên. Phải dùng runner chung hoặc kế thừa luồng chuẩn O(1).
- **Subagent Routing:** Worker subagent cho thiết bị Android mặc định chạy Gemini pool (`ag-gemini-pool-3`), Luna chỉ dùng làm fallback khi nghẽn.

## 2. Điểm Chạm Mở "Sửa Hồ Sơ" Trên Layout TikTok Mới (v47+ Center Avatar)
Trên Samsung S7 (1080x1920), TikTok có 2 dạng layout Profile:
- **Layout Cũ / Creator (Avatar lệch trái):** Nút "Sửa hồ sơ" to dưới stats hoặc icon cây bút chì ở góc trên bên trái `XY_EDIT_PENCIL = (72, 148)`.
- **Layout Mới (Avatar ở giữa, tài khoản chưa có bio):**
  - Góc trên bên trái `(72, 148)` là icon **Tìm bạn bè** (icon người +) -> CẤM bấm.
  - Bên dưới stats chỉ có nút `+ Thêm tiểu sử` (`(540, 867)`) -> bấm vào chỉ mở trang nhập bio.
  - Dòng tên ở giữa `(540, 560)` -> bấm vào sẽ mở menu chuyển tài khoản (Account Switcher).
  - **ĐIỂM CHẠM CHUẨN XÁC 100%:** Icon cây bút chì ẩn nằm ngay bên phải dòng tên `com.ss.android.ugc.trill:id/t_3`:
    - Bounds UI: `[798, 516][942, 600]`
    - Tọa độ tâm: **`(870, 558)`**
    - Chạm vào `(870, 558)` sẽ mở trực tiếp màn hình **`Sửa hồ sơ`**!

## 3. Quy Trình Nhập Tên & Xác Nhận
1. Mở `Sửa hồ sơ` (`com.ss.android.ugc.trill:id/pvp`).
2. Chạm dòng Tên: `com.ss.android.ugc.trill:id/dui` tại `(540, 753)`.
3. Màn hình đổi tên: input box `hv4` tại `(540, 576)` -> xóa tên cũ tại `(960, 576)` -> chuyển `AdbKeyboard` -> nhập base64 -> bấm **Lưu** tại `(990, 138)`.
4. Popup 7 ngày: chạm **Xác nhận** tại `(750, 1175)` (`bounds=[541, 1104][960, 1247]`).
5. Khôi phục bàn phím Samsung gốc -> Bấm Back về Profile -> Nghiệm thu ảnh/OCR.

## 4. Xử Lý Kẹt Device Lock Do Tiến Trình Chết
Khi runner nền crash hoặc bị kill để lại `machine_<N>.lock.json` làm kẹt lock 300s:
- Chạy canonical reaper:
  ```bash
  python "D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py"
  ```
