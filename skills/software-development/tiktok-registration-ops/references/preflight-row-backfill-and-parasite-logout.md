# Preflight Row Provisioning & MACHINE_FULL_8_ACCOUNTS Recovery

Quy trình chuẩn xử lý sự cố Preflight Reg bù (`ensure_row_accounts.py <row>`) khi báo lỗi trần 8 tài khoản:
`Máy N: Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)` hoặc `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS`.

---

## 1. Bản chất sự cố
- Trước mỗi ca nuôi tài khoản, tiến trình Preflight (`ensure_row_accounts.py <row>`) kiểm tra `taikhoan_run_safe.xlsx`.
- Nếu phát hiện máy nào có Row đó đang để trống (`ID = None`), hệ thống tự động kích hoạt tiến trình mua Hotmail và chạy `_run_all_targets.py` để reg bù nick.
- Khi vào app TikTok mở Switcher để bấm "Thêm tài khoản", TikTok phát hiện app đã đủ 8 nick nên ẩn nút "Thêm tài khoản", văng ngoại lệ `MACHINE_FULL_8_ACCOUNTS`.

---

## 2. Quy trình phân loại 2 nguyên nhân gốc rễ (Root Cause Classification)

Cần inspect O(1) ngay bằng cách đọc ảnh Switcher lưu tại `D:/Taadaa/Tiktok_Reg/screenshots_social/<N>_03_dropdown_*.png` hoặc dump UI `fail_04_add_account_*.xml` kết hợp WinRT OCR:

### Loại A — Lệch Excel / Thất lạc vị trí (Displaced Account)
* **Dấu hiệu:** Nick hiển thị trên màn hình máy thật là nick chính chủ được reg trên chính máy đó (kiểm tra `tracking_result_stt<N>_*.json` trong `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/` có cùng serial và STT). Nhưng trong `taikhoan_dat_v2_updated .xlsx`:
  - Dòng Row của Máy N đang ghi `ID = None`.
  - Nick đó lại bị lưu nhầm sang dòng của một máy khác (gây duplicate).
* **Quy trình xử lý:**
  1. Tạo backup `taikhoan_dat_v2_updated .xlsx.bak-<tag>-<timestamp>`.
  2. Cập nhật (backfill) username, password, email, pass mail, ngày tạo vào đúng dòng `(Machine N, Slot)` trên `taikhoan_dat_v2_updated .xlsx`.
  3. Xóa các ô duplicate trên dòng máy bị ghi nhầm về `None`.
  4. Chạy `D:/Taadaa/python-envs/automation/Scripts/python.exe "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"`.
  5. Đối soát lại bằng `ensure_row_accounts.get_missing_machines_for_row(<row>)` để đảm bảo Máy N đã thoát khỏi danh sách thiếu.

### Loại B — Nick ký sinh (Parasite Account - Log chéo)
* **Dấu hiệu:** Nick thứ 8 trên thiết bị thực tế là tài khoản chính chủ của một máy khác (đã có trong Excel ở máy khác và máy đó cũng đang chạy nuôi).
* **Quy tắc an toàn Farm:**
  - Tuyệt đối KHÔNG can thiệp ADB khi máy đang bận ca chạy chính (`machine_N.lock.json` tồn tại).
  - Canh máy rảnh (0 lock) mới được can thiệp.
* **Quy trình xử lý:**
  1. Dùng lệnh chuẩn:
     `python D:/Taadaa/tools/do_logout_account.py <machine_id> <parasite_username> <serial>`
  2. Quy trình tự động thực hiện:
     - Giành device lock cho thiết bị.
     - Mở Switcher -> chuyển sang nick ký sinh.
     - Vào Cài đặt và quyền riêng tư -> cuộn xuống đáy -> bấm Đăng xuất -> xác nhận popup Đăng xuất.
     - Mở lại Switcher kiểm chứng: nick ký sinh đã biến mất, số nick còn lại = 7, nút *"Thêm tài khoản"* đã hiển thị trở lại.
     - Chụp ảnh nghiệm thu `D:/Taadaa/reports/m<N>_verified_logout.png` (`CAPTURE-BEFORE-CLEANUP`) TRƯỚC KHI force-stop và đưa máy về Home.
     - Nhả device lock an toàn.

---

## 3. Kỷ luật phản hồi Coordinator với User
- Khi nhận Farm Alert dạng `[PREFLIGHT REG BÙ ROW N]`:
  - **CẤM TUYỆT ĐỐI** hỏi ngược lại user các câu hỏi điều phối rườm rà như: *"Bạn muốn xử lý máy nào trước?"*, *"Ưu tiên theo thứ tự nào?"*.
  - User coi việc hỏi này là lúng túng / thiếu chủ động và sẽ phản ứng gay gắt (`???`, `Xử lý đi`).
  - Coordinator phải lập tức inspect O(1), phân định rõ máy nào thuộc Loại A (cần sửa Excel), máy nào thuộc Loại B (cần logout), trình bày bằng chứng ngắn gọn và chủ động dispatch worker thực thi ngay.
