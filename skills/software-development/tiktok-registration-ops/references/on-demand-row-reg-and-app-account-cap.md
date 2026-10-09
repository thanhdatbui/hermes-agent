# On-Demand Row Reg Provisioning & TikTok 8-Account App Ceiling

## 1. Cơ Chế On-Demand Row Reg Provisioning (`ensure_row_accounts.py`)
Được thiết kế để giải quyết triệt để tình trạng máy farm bị trống nick khi đến lượt nuôi acc theo Row (1..8).

### Quy trình tự động trong `tiktok_runner.py`:
1. Trước khi spawn tiến trình nuôi acc cho Row $N$, hook `_preflight_ensure_accounts(row, window_key)` được kích hoạt.
2. Launcher gọi script `D:/Taadaa/tools/ensure_row_accounts.py <row>`:
   - **Bước 1 (Inspect Missing):** Quét cột ID của toàn bộ 80 máy tại Row $N$ trong `taikhoan_run_safe.xlsx`.
   - **Bước 2 (Mail Provisioning):** Đối chiếu với kho `gmail_clean_v2.xlsx`. Nếu máy nào chưa có sẵn mail -> tự động gọi `buy_hotmail.py` mua Hotmail OAuth2 và nạp vào máy đó.
   - **Bước 3 (Targeted Batch Reg):** Thiết lập biến môi trường `TIKTOK_REG_TARGET_STTS=<m1,m2,...>` và gọi `D:/Taadaa/Tiktok_Reg/_run_all_targets.py` để chỉ reg đúng các máy thiếu này.
   - **Bước 4 (Auto Merge & Sync):** Quét các file `tracking_result_*.json` mới nhất, tự động ghi thông tin nick mới vào `taikhoan_dat_v2_updated .xlsx` đúng vị trí Row $N$, sau đó kích hoạt `taikhoan_sync_cron_launcher.py` để đồng bộ ngay sang `taikhoan_run_safe.xlsx`.

> ⚠️ **Lưu ý đồng bộ đa máy (Admin vs Kibe):**
> Script `ensure_row_accounts.py` và hook trong `tiktok_runner.py` phải luôn được đồng bộ qua OneDrive Shared / Git deploy. Nếu farm Kibe chạy bản runner cũ chưa có preflight hook, runner sẽ bỏ qua các máy trống mà không kích hoạt reg bù.

---

## 2. Pitfall: TikTok App Chạm Trần Tối Đa 8 Tài Khoản (`[04_add_account]`)

### Triệu chứng:
Batch reg bị crash với ngoại lệ:
```
RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', 'Thêm tài khoản khác', 'Add another account', 'add_account')
```

### Nguyên nhân cốt lõi:
- Ứng dụng TikTok Android có giới hạn cứng: **chỉ cho phép lưu tối đa 8 tài khoản đăng nhập trên một thiết bị cùng một lúc**.
- Khi một máy đã có đủ 8 tài khoản lưu trong app (có thể do các đợt reg trước, hoặc do tài khoản từ máy khác từng đăng nhập nhầm vào máy này), sheet dropdown **"Chuyển đổi tài khoản" sẽ ẩn hoàn toàn nút "Thêm tài khoản"** (Add account).
- Khi kiểm tra file UI dump XML (`fail_04_add_account_*.xml`), sẽ thấy có đủ 8 item tài khoản dạng `com.ss.android.ugc.trill:id/lpw`.

### Cách xử lý:
1. Tuyệt đối không cố gắng retry reg trên máy này vì giao diện không còn nút bấm.
2. Kiểm tra danh sách 8 nick trong XML với workbook `taikhoan_dat_v2_updated .xlsx` để xác định nick nào là nick lạ/nhầm (ví dụ nick của STT khác).
3. Đăng nhập vào nick lạ đó trong app, thực hiện Đăng xuất (Logout) để giải phóng slot về < 8 nick. Khi đó nút "Thêm tài khoản" sẽ tự động xuất hiện trở lại.

---

## 3. Pitfall: Watchdog Feed Session Ngộ Nhận Batch Bị Device Lock Là Lỗi Hệ Thống

### Triệu chứng:
Watchdog gửi Farm Alert báo toàn bộ farm (78/80 máy) bị Fail với 0 tim, 0 video, trong khi phiên chạy thật vẫn đang hoạt động tốt trên máy thật (>90% success).

### Nguyên nhân:
1. Khi một tiến trình runner thứ 2 vô tình bị trigger lặp trong lúc tiến trình chính đang giữ device lock của toàn bộ máy farm, runner thứ 2 kết thúc ngay sau vài giây với `skipped-device-locked: 78`.
2. Hàm `parse_run_all` của watchdog khi đọc fallback `summary.txt` ở root của batch run rác đã gán `status: fail, reason: batch-config-error` cho tất cả các máy.
3. Việc gán này làm vô hiệu hóa bộ lọc `is_device_locked_skip`, khiến watchdog ngộ nhận 78 máy đã hoàn tất thật và kích hoạt điều kiện gửi báo cáo ảo đè lên phiên chính.

### Quy tắc chuẩn hóa:
- Watchdog phải luôn ưu tiên đọc file `log.jsonl` tại run root để lấy đúng giá trị `result` (`skipped-device-locked`) cho từng máy.
- Tuyệt đối không bao giờ chốt báo cáo khi phiên vẫn còn máy bị vướng lock chưa chạy xong (`has_unattempted_locked == True` hoặc `runner_busy == True`).
