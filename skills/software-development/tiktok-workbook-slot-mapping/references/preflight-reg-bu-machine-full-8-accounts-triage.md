# Playbook Xử lý Lỗi Preflight Reg Bù [04_add_account] MACHINE_FULL_8_ACCOUNTS

## 1. Triệu chứng & Tình huống xuất hiện
- Khi kịch bản tự động `ensure_row_accounts.py <Row>` chạy trước ca nuôi (preflight provisioning), hệ thống quét tìm các máy thiếu account ở Row đó trong `taikhoan_run_safe.xlsx`.
- Với máy được chọn đi reg, runner khởi động TikTok, mở Account Switcher Dropdown (`com.ss.android.ugc.trill:id/q3t` / `oly`), đếm số account node hiện diện (`resource-id` khớp `n72`, `lkp`, `l9b`, `lpw`, `l_z`, `lrq`, `lli`).
- Nếu số node $\ge 8$, runner ném ngoại lệ:
  ```text
  RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok
  ```
- Bot Telegram bắn alert về group:
  ```text
  📋 [PREFLIGHT REG BÙ ROW X]
  • Tổng máy thiếu: 1 (Đã chạy: 1, Cooldown: 0)
  ❌ Thất bại (1):
    - Máy M: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị
  • Thời gian: ...
  • Hiện trường: D:/Taadaa/Tiktok_Reg/screenshots_social/
  ```

---

## 2. Bản chất kỹ thuật & Root Causes
1. **Lệch pha dữ liệu giữa App TikTok thật và Excel (Data Drift / Ghost Missing)**:
   - TikTok trên thiết bị Samsung thực tế đã đăng nhập đủ 8 tài khoản (trần tối đa của ứng dụng). Nút "Thêm tài khoản" bị app TikTok ẩn hoàn toàn.
   - Nhưng trong `taikhoan_dat_v2_updated .xlsx` (hoặc `taikhoan_run_safe.xlsx`), một ô ở Row K của máy đó lại đang trống (`ID = None | GMAIL = None`).
2. **Các nguyên nhân làm trống ô Excel dù máy đã có nick**:
   - **Ghi đè slot do nạp deferred nhầm dòng**: Nick đã được reg trước đó (có lưu JSON deferred tracking trong `artifacts/runs/social-batch-all/...`), nhưng khi một nick khác reg sau apply vào Excel đã ghi đè hoặc làm mất dấu nick cũ.
   - **User dọn dẹp duplicate nhưng chưa sync / xoá nhầm**: Khi dọn dẹp slot hoặc copy paste Excel bị lệch hàng.
   - **Nick ký sinh (Parasite Account)**: Nick của máy khác vô tình được login trên máy này, chiếm mất 1 slot khiến máy chạm trần 8 nick.

---

## 3. Quy trình điều tra O(1) & đối soát hiện trường
**Kỷ luật bất biến**: CẤM tự ý ADB can thiệp, logout hay xóa nick trên máy khi chưa đối soát.

### Bước 1: Trích xuất ảnh Dropdown Switcher hiện trường
- Ảnh được lưu tự động tại `D:/Taadaa/Tiktok_Reg/screenshots_social/<M>_03_dropdown_<timestamp>.png` (hoặc trong thư mục run gần nhất `D:/Taadaa/runtime/kibe/artifacts/runs/social-batch-all/<run_id>/batch_*/stt_<M>/`).
- Chạy WinRT OCR đọc danh sách 8 handle đang login trên app:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:/Taadaa/do_ocr.ps1" "D:\Taadaa\Tiktok_Reg\screenshots_social\<M>_03_dropdown_<time>.png"
  ```

### Bước 2: Đối chiếu 8 handle OCR với Master Workbook
- Mở `taikhoan_dat_v2_updated .xlsx` tại các dòng của Máy M (`(M-1)*8 + 1` đến `(M-1)*8 + 8`).
- So sánh từng handle trên màn hình với 8 dòng của máy:
  - 7 nick khớp với 7 dòng đã có ID.
  - Tìm ra nick thứ 8 (ví dụ `@joseavnyd0b`) hiển thị trên app nhưng dòng tương ứng trên Excel đang là `None`.

### Bước 3: Truy vết thông tin Credentials gốc của Nick bị sót
- Tìm trong lịch sử tracking JSON hoặc file log reg:
  - Quét `artifacts/runs/social-batch-all/**/stt_<M>/tracking_result_*.json`.
  - Hoặc tìm trong `social_reg_log.txt` với từ khóa handle của nick:
    ```python
    # Tìm nhanh trong 50MB cuối của log reg
    with open('D:/Taadaa/Tiktok_Reg/social_reg_log.txt', 'rb') as f:
        f.seek(-50000000, 2)
        chunk = f.read().decode('utf-8', errors='ignore')
        for line in chunk.splitlines():
            if '<handle_can_tim>' in line:
                print(line)
    ```
- Trích xuất đủ: `email`, `password`, `mail_password`, `dob`, `created_date`.

---

## 4. Giải pháp xử lý triệt để
1. **Trường hợp Nick thuộc về chính máy đó (bị sót trên Excel)**:
   - Điền lại thông tin nick vào đúng Slot K (dòng `(M-1)*8 + K`) trong `taikhoan_dat_v2_updated .xlsx`.
   - Chạy `taikhoan_sync_cron_launcher.py` để đồng bộ sang `taikhoan_run_safe.xlsx`.
   - Preflight đợt tiếp theo sẽ thấy máy đã đủ 8 nick và không kích hoạt reg bù nữa.
2. **Trường hợp Nick là nick ký sinh (chính chủ máy khác)**:
   - Kiểm tra xem nick đó máy chính chủ đã đăng nhập chưa.
   - Nếu máy chính chủ đã có nick đó: lên kế hoạch an toàn (qua Event-Driven Watchdog ngoài giờ ca chính) để logout nick ký sinh ra khỏi Máy M nhằm nhả 1 slot trống cho reg bù.
