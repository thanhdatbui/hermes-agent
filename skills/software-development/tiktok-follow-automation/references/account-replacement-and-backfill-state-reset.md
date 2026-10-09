# Kỷ Luật Reset State & Bộ Đếm Khi Thay Nick / Reg Bù (Account Replacement Reset Protocol)

## 1. Bản Chất Kiến Trúc Gây Ra Drift
Khi một tài khoản TikTok trên farm bị die và được thay thế bằng tài khoản mới reg (ví dụ `@anhdo829` die trên Máy 20 Slot 1, thay bằng `@javialdzxxj`):
1. **State Follow lưu theo `(Machine, Slot)` chứ không theo `Username`**:
   - File state: `runs/state/follow_state_{machine}_row_{account_row_index}.json` (ví dụ `follow_state_20_row_1.json`).
   - Runner không tự động xóa file này khi đổi username trong Excel.
   - Kết quả: File state vẫn giữ nguyên 100+ UID đã follow trong quá khứ của nick cũ, cooldown history, và fail streak cũ.
2. **Cơ chế Sync 1-chiều bảo toàn bộ đếm (`sync-tik-workbooks.py`)**:
   - Khi cập nhật ID mới vào Master DAT (`taikhoan_dat_v2_updated .xlsx`) và chạy sync sang `TikN.xlsx`, script cố tình **bảo toàn cột `Video Đã Đăng`**.
   - Cột `Video Đã Đăng` trong `TikN.xlsx` và `taikhoan_run_safe.xlsx` vẫn giữ nguyên số video của nick cũ (ví dụ: `22`).
3. **Dual Gate Follow bị bypass ngoài ý muốn**:
   - Dual Gate (`follow_runner/core/follow_state.py`): Điều kiện cấp budget follow là `account_age_days >= 30` VÀ `video_count >= 10`.
   - Hệ thống follow đọc `video_count` từ cột `Video Đã Đăng` trong `taikhoan_run_safe.xlsx` và tính `account_age_days` từ `Ngày Tạo`.
   - Nếu không reset `Video Đã Đăng` về 0 và không cập nhật `Ngày Tạo` mới, nick mới vừa reg sẽ bị nhận diện nhầm thành **Trưởng thành (Full budget 10–20 lượt)** và bị mang đi follow chéo ngay lập tức.

## 2. Rủi Ro Vận Hành Nếu Không Reset
- **Bị TikTok trảm tức thì (Immediate Ban/Shadowban)**: Nick mới tinh chưa có Inbound Trust, chưa đủ 30 ngày ngâm và chưa đủ 10 video mà đã đi follow chéo hàng loạt sẽ bị thuật toán TikTok gắn cờ bot/spam, silent drop follow hoặc khóa vĩnh viễn.
- **Nhảy cóc video upload (Video Upload Skipping)**: Runner đăng video (`run_post.py`) tính `next_video = Video Đã Đăng + 1 = 23`. Bot sẽ bỏ qua từ video 1 đến 22 trong folder video nguồn, bắt đầu đăng từ clip 23. Kho 45 video sẽ cạn chỉ sau 22 ngày.
- **Nhiễm bẩn Dedupe Follow**: Acc mới sẽ không thể follow các tài khoản trùng với danh sách đã follow của acc cũ do bị dedupe filter chặn.

## 3. Quy Trình 4 Bước Chuẩn Hóa Khi Thay Nick Mới (Bắt Buộc)

```
[Thay Nick Die -> Nick Mới]
         │
         ├── 1. Master DAT: Ghi ID mới, mail, pass, và ĐÚNG NGÀY REG MỚI vào cột 'NGÀY TẠO'
         ├── 2. TikN.xlsx: Reset cột 'Video Đã Đăng' = 0 (dòng máy M)
         ├── 3. Sync Workbooks: Chạy sync-safe-workbook.py để cập nhật sang taikhoan_run_safe.xlsx
         └── 4. Follow State: Xóa file runs/state/follow_state_{M}_row_{slot}.json
```

### Bước 1: Master DAT (`taikhoan_dat_v2_updated .xlsx`)
- Ghi ID mới, GMAIL, PASS MAIL, PASS TT.
- **BẮT BUỘC cập nhật cột `NGÀY TẠO`**: Điền ngày tạo thực tế của nick mới (ví dụ: ngày vừa reg). CẤM giữ nguyên ngày tạo của nick cũ.

### Bước 2: Reset `Video Đã Đăng` = 0 trong `TikN.xlsx`
- Mở `Tik<N>.xlsx` tương ứng (`N = ((Folder - 1) % 8) + 1`).
- Tại dòng của Máy $M$:
  * Đặt cột `Video Đã Đăng` = `0`.
  * Đặt cột `Kiểm Tra Dữ Liệu` = `'OK'`.
  * Nếu dùng folder video mới, cập nhật lại số `Folder Video` và `video gốc`.

### Bước 3: Đồng bộ Safe Workbook
- Chạy:
  `python D:/Taadaa/tiktok-luot\ nuoi\ acc/scripts/sync-safe-workbook.py`
- Kiểm tra `taikhoan_run_safe.xlsx` tại dòng Máy $M$, Slot $N$:
  * `Video Đã Đăng` = `0`
  * `Ngày Tạo` = Ngày reg mới.
- Chạy preflight validator:
  `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/<cluster> --exit-on-error`

### Bước 4: Tẩy trắng State Follow
- Xóa file state của slot tương ứng:
  `D:/Taadaa/tiktok-follow/runs/state/follow_state_{M}_row_{N}.json`
- Khi xóa file này:
  * Runner khởi tạo lại `followed = {}`, `fail_streak = 0`.
  * Do `video_count = 0` và `account_age_days < 30`, Dual Gate sẽ tự động gán **`budget = 0`** (chế độ Dưỡng Sinh / nghỉ dưỡng), bảo vệ nick an toàn tuyệt đối cho đến khi trưởng thành.

### Bước 5: Cập nhật CSDL SQLite Tracker (`tiktok_tracker.db`)
Bảng `account_mapping` và `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db` phục vụ theo dõi sức khỏe farm và đối soát watchdog:
```sql
DELETE FROM account_mapping WHERE may = <may> AND tik = <slot>;
DELETE FROM account_mapping WHERE username = '<old_username>';
INSERT OR REPLACE INTO account_mapping (username, may, tik) VALUES ('<new_username>', <may>, <slot>);
```
Chạy script đồng bộ farm account info nếu cần:
`python D:/Taadaa/tools/sync_farm_account_info.py`
