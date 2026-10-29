# False-Positive Follow Drop (Anchor Check Race) & New Profile Edit Unlock

## 1. False-Positive Anchor Follow Drop (35 Machines Shadow-Drop Illusion)
### Hiện tượng
Trong các ca chạy nuôi TikTok (Mode 2: Follow Followers), watchdog hoặc runner báo cáo hàng loạt máy (ví dụ 35/38 máy) bị:
`FOLLOW_FAILED: anchor @<uid> bị nhả sau vuốt — dừng session` -> `Nhả liền 35 máy | 0 lượt`.

### Nguyên nhân gốc (Root Cause)
1. Trong `mode2_follow_followers.py` (`_ensure_anchor_followed`):
   - Bot bấm nút Follow Anchor (`_tap_follow_button`).
   - Script chỉ ngủ cứng `time.sleep(1.0)` rồi gọi ngay `ocr_screen()` để phân loại trạng thái nút (`classify_button_from_ocr`).
2. Do độ trễ mạng Proxy MikroTik hoặc server TikTok cập nhật UI chậm (> 1.0s), nút trên màn hình chưa kịp đổi nhãn sang "Đang follow" (hoặc icon chuyển trạng thái).
3. Script nhận diện `not_followed` ➔ lập tức gán `follow_failed = True` và dừng toàn bộ session của máy đó ngay tại Anchor đầu tiên, khiến toàn bộ danh sách 10-20 user đằng sau bị bỏ qua hoàn toàn.

### Kỷ luật Triage & Khắc phục
- **Không đoán mò:** CẤM suy diễn là "nick mới bị TikTok phạt", "chưa đủ video" hay "thiếu tương tác". BẮT BUỘC đọc file log thực tế `machines/machine_<N>/<run_id>/follow_result.json` để bóc tách đúng `status` và `reason`.
- **Hạ tầng sửa đổi:** Thêm progressive polling (kiểm tra lặp lại 2-3 lần với khoảng cách 1.5s - 2.0s hoặc lướt nhẹ refresh profile) trước khi phán quyết Anchor bị nhả thật.

---

## 2. Samsung S7 / New TikTok Profile: Nút Sửa Hồ Sơ & Mở Khóa Đổi Username
### Hiện tượng
Giao diện Profile TikTok mới trên Samsung S7 (1080x1920) khi tài khoản chưa có Bio:
- Không hiển thị nút chữ `Sửa hồ sơ`.
- Nút `+ Thêm tiểu sử` chiếm vị trí trung tâm `[36, 684][887, 768]`.
- Bấm vào tên nickname `Lý Thị Hoàn1` mở Account Switcher (chuyển đổi tài khoản) thay vì sửa tên.
- Bấm vào ID `@user...` bị chuyển hướng vào form nhập Tiểu sử.

### Cách vào màn hình "Sửa hồ sơ" chuẩn để đổi Username:
1. **Bước 1 (Mở khóa Bio):**
   - Tap vào `+ Thêm tiểu sử` (tọa độ `y ~ 720..740`).
   - Nhập một câu Bio bất kỳ qua ADB / AdbKeyboard (ví dụ: `Am nhac moi ngay`) ➔ Bấm **Lưu** (`[953, 133][1029, 168]` ở góc trên bên phải).
2. **Bước 2 (Vào Sửa hồ sơ):**
   - Sau khi có Bio, dòng chữ Bio xuất hiện trên Profile (`y ~ 680..720`).
   - **Tap thẳng vào dòng chữ Bio vừa tạo** (ví dụ `(211, 706)`).
   - TikTok sẽ mở ra trang **`Sửa hồ sơ`** đầy đủ (gồm: Thay đổi ảnh, Tên, Tên người dùng `@`, Tiểu sử).
3. **Bước 3 (Đổi Username `@`):**
   - Tap vào dòng `Tên người dùng` (`[445, 874][762, 915]`).
   - Xóa chuỗi cũ, nhập username mới (ví dụ `lyhoan.music`).
   - Bấm **Lưu** góc trên bên phải ➔ Bấm **Xác nhận** popup *"Cập nhật tên người dùng (30 ngày đổi 1 lần)"* tại `[644, 1222][853, 1259]`.
4. **Bước 4 (Atomic Sync):** Đồng bộ nguyên tử ngay lập tức vào Excel phân ca (`Tik<N>.xlsx`), master excel (`taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`) và SQLite `tiktok_tracker.db` (`account_mapping`, `farm_account_info`).
