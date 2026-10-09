# Preflight Reg Bù: Máy Đã Đủ 8 Acc & Chuỗi Đồng Bộ Reconcile Chuẩn Hóa

> **Date:** 2026-10-08  
> **Trigger:** Farm Alert: `[PREFLIGHT REG BÙ ROW N] ❌ Thất bại: Máy M: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)`

---

## 1. Bản Chất Sự Cố & Dấu Hiệu Nhận Biết
- **Hiện tượng**:
  Khi cron hoặc preflight quét `taikhoan_run_safe.xlsx` ở Row $N$ thấy máy $M$ bị trống (`None`), hệ thống phát động lệnh reg bù `ensure_row_accounts.py N`. Khi runner mở app TikTok và bung Switcher ("Chuyển đổi tài khoản"), app TikTok trên thiết bị vật lý đã có đủ 8 tài khoản -> ẩn nút "Thêm tài khoản" -> văng ngoại lệ `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`.
- **Gốc rễ**:
  1. Trong một batch reg trước đó (ví dụ `social-batch-all`), máy $M$ đã đăng ký thành công tài khoản TikTok (thường qua flow Hotmail/Outlook + OTP).
  2. Tại thời điểm kết thúc batch, hàm `_acquire_workbook_write_lock` cố gắng mở Master Excel độc quyền tuyệt đối (`dwShareMode=0`). Nếu OneDrive đang đồng bộ nền hoặc Excel đang mở, tiến trình văng `FAILED_SYNC_OSError`.
  3. Runner lưu kết quả hoãn (deferred) vào file JSON `tracking_result_stt<M>_<email>.json` trong thư mục `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/<run>/batch_*/stt_<M>/`.
  4. Do không có cơ chế retry tự động nạp bù, file Excel Master `taikhoan_dat_v2_updated .xlsx` tại dòng của máy $M$ vẫn giữ nguyên giá trị `None`, tạo ra sự lệch pha (drift) giữa thiết bị vật lý (8 acc) và Excel (7 acc).

---

## 2. Quy Trình Điều Tra O(1) Nhanh
1. **Kiểm tra trạng thái máy vật lý**:
   - Chạy: `python D:/Taadaa/tools/inspect_machine.py <M>`
   - Xác nhận serial và tình trạng màn hình.
2. **Truy xuất JSON kết quả bị kẹt**:
   - Đọc `all_results.json` trong thư mục run gần nhất của `D:/Taadaa/runtime/<cluster>/artifacts/runs/social-batch-all/`.
   - Lọc bản ghi có `"stt": M, "status": "SUCCESS", "workbook_write": "FAILED_SYNC_OSError"`.
   - Mở file `tracking_result_stt<M>_<email>.json` tương ứng để lấy:
     * `tiktok_id`
     * `email`
     * `mail_password`
     * `password` (Lưu ý: Luồng đăng ký qua OTP / email-only thì password TikTok để trống `""` hoặc `None`, **CẤM** tự ý bịa password).
     * `created_date`
     * `serial`
3. **Xác minh hình ảnh thực tế qua WinRT OCR (Bắt buộc)**:
   - File JSON chứa đường dẫn `proof_screenshot` (ảnh `profile_<stt>_after_ensure_*.png`).
   - Chạy WinRT OCR kiểm tra:
     `python "C:/Users/Kibe/AppData/Local/hermes/skills/productivity/windows-native-ocr/scripts/winrt_ocr.py" "<proof_screenshot_path>"`
   - Bắt buộc xác nhận: username `@<tiktok_id>`, tab Hồ sơ active, 0 Follow/0 Follower.

---

## 3. Quy Trình 3 Bước Reconcile Chuẩn Hóa (Standard 3-Step Reconcile Pipeline)
*Tuyệt đối không sửa lẻ tẻ bằng tay trên từng file Tik1..Tik8.xlsx hay taikhoan_run_safe.xlsx để tránh lỗi lệch công thức hoặc xung đột lock.*

### Bước 1: Nạp Master DAT
- **Đường dẫn**: `D:/OneDrive/TaadaaData/<cluster>/taikhoan_dat_v2_updated .xlsx`
- **Sao lưu trước khi ghi**: Tạo backup `.bak_before_backfill_<timestamp>` bằng `shutil.copy2`.
- **Xác định dòng mục tiêu**:
  * Cluster Kibe ($M \le 80$): Folder Video $= (M - 1) \times 8 + \text{slot}$.
  * Cluster Admin ($M \ge 201$): Folder Video $= (M - 201) \times 8 + \text{slot}$.
  * Tìm dòng có Cột 1 $= M$ và Cột 2 $=$ Folder Video.
- **Điền dữ liệu & Xóa Stale Cache Cũ (Bắt buộc)**:
  * Cột 3 (ID): `tiktok_id`
  * Cột 4 (PASS): `password` hoặc `None` (nếu reg OTP)
  * Cột 5 (2FA): BẮT BUỘC gán `None` (xóa triệt để 2FA secret của acc cũ trước đó)
  * Cột 6 (GMAIL): `email`
  * Cột 7 (PASS MAIL): `mail_password`
  * Cột 8 (DOB): BẮT BUỘC gán `None` (xóa triệt để ngày sinh cũ của acc cũ)
  * Cột 9 (NGÀY TẠO): `created_date`
  * Cột 10 (device ID): `serial`

### Bước 2: Kích Hoạt Tự Động Đồng Bộ Workbook & CSDL
1. **Đồng bộ chuỗi Workbook qua Cron Launcher**:
   ```bash
   python "C:/Users/Kibe/AppData/Local/hermes/scripts/taikhoan_sync_cron_launcher.py"
   ```
   *Launcher tự động thực thi hai việc:*
   - `sync-tik-workbooks.py`: Đồng bộ 1-chiều ID từ Master DAT sang `Tik<Slot>.xlsx`, chuyển cột kiểm tra dữ liệu từ `MISSING_ID` sang `OK`.
   - `sync-safe-workbook.py`: Tự động dồn toa (contiguous slot packing) và cập nhật số lượng video sang `taikhoan_run_safe.xlsx`.
2. **Đồng bộ CSDL SQLite `farm_account_info`**:
   ```bash
   python D:/Taadaa/tools/sync_farm_account_info.py
   ```
   *Đảm bảo bảng `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db` khớp 1:1 với Master Excel, mapping chính xác badge `M{may} · T{tik}`.*

### Bước 3: Kiểm Chứng Invariant 2 Lớp Bắt Buộc
1. **Lớp 1 - Validator toàn bộ Excel**:
   ```bash
   python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/<cluster> --exit-on-error
   ```
   *Yêu cầu bắt buộc:* Exit code 0 (`0 lỗi FAIL, 0 cảnh báo WARN`).
2. **Lớp 2 - Dry-Run Preflight Reg Bù**:
   ```bash
   python D:/Taadaa/tools/ensure_row_accounts.py --dry-run <slot>
   ```
   *Yêu cầu bắt buộc:* Thông báo xác nhận toàn bộ máy đã đầy đủ tài khoản:
   `[ensure_row] [<CLUSTER>] Row <slot>: Toan bo may da day du tai khoan! Khong can reg.`

### Bước 4: Kiểm Chứng Live Canary Trên Thiết Bị Thật (Targeted Machine Canary)
- **Lệnh thực thi chuẩn**:
  ```bash
  python D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py --mode multi-machine-feed-session --machines <M> --account-workbook "D:/OneDrive/TaadaaData/<cluster>/taikhoan_run_safe.xlsx" --account-row-index <slot> --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --prepare-tiktok --recovery-test-swipes 1 --config "D:/Taadaa/tiktok-luot nuoi acc/python_runner/config.example.yaml"
  ```
  *(Lưu ý: Cờ `--prepare-tiktok` chỉ hỗ trợ các chế độ batch như `multi-machine-feed-session`, cấm truyền vào `feed-session-smoke` để tránh `CONFIG_ERROR`).*
- **Tiêu chuẩn nghiệm thu**:
  1. Exit code 0 (`Status: success`).
  2. Switcher nhận diện chính xác username mới, verify profile thành công.
  3. Bắt buộc chụp ảnh Profile/Switcher sau khi switch và soi mắt kiểm chứng bằng WinRT OCR trước khi gửi `MEDIA:<path>` cho User.
