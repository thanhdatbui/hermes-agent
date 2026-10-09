# Pitfall: Cross-Machine Duplicate Email, Deferred Dedup Flaw & TikTok 8-Account Limit

## Sự cố điển hình (Hiện trường 2026-09-08 & Root Cause 2026-08-26)
- **Triệu chứng:** Máy STT 03 chạy Reg ban đêm fail 100% tại `fail_04_add_account` vì không thấy nút "Thêm tài khoản".
- **Điều tra hiện trường:** XML dump xác nhận máy STT 03 đã có đủ 8 nick trên app (chạm trần tối đa của TikTok), trong đó có nick `miumiu67971`.
- **Đối chiếu chéo:** Nick `miumiu67971` trên Excel tracking (`taikhoan_dat_v2_updated .xlsx`) lại được ghi nhận cho máy STT 05 (Row 40). Kiểm tra app trên máy STT 05 cũng đang chứa nick `miumiu67971`.
- **Hệ quả:** 1 tài khoản bị đăng nhập trên 2 máy cùng lúc, Excel ghi lệch máy, máy STT 03 bị đầy cứng 8 nick nhưng Excel tưởng mới có 7 nick nên liên tục cử đi reg rồi crash batch.

---

## 3 Nguyên nhân gốc rễ liên hoàn

### 1. Phân bổ trùng email trong kho nguồn (`gmail_clean_v2.xlsx`)
- Khi nạp lô mail vào kho nguồn, cùng 1 email (ví dụ `karistinelso@hotmail.com`) bị gán cho cả máy A (STT 03) và máy B (STT 05) do trượt dòng hoặc chia pool không khử trùng lặp.

### 2. Cuộc đua giữa Deferred Write và Batch Recovery
- **Batch 1 (07:51):** Máy A và Máy B chạy song song.
  - Máy A bốc email khác trước bị timeout.
  - Máy B bốc `karistinelso@hotmail.com`, đăng ký thành công nick `miumiu67971` lúc 08:02. Kết quả lưu file JSON deferred `tracking_result_stt5_...json`, **chưa ghi ngay vào file Excel**.
- **Batch 2 (09:48 - Recovery):** Máy A chạy lại ca lỗi.
  - Máy A đọc Excel tracking thấy `karistinelso@hotmail.com` vẫn chưa có TikTok ID (vì deferred chưa merge).
  - Máy A bốc tiếp mail này điền vào TikTok.
  - TikTok phát hiện mail đã đăng ký -> tự động chuyển sang luồng **Đăng nhập (Login)** -> lấy OTP Graph API và đăng nhập nick `miumiu67971` vào Máy A lúc 09:56.
  - Kết quả: Tạo thêm 1 file JSON deferred `tracking_result_stt3_...json`.

### 3. Khiếm khuyết khử trùng lặp trong Tool Merge (`apply_deferred_tracking_results.py`)
- Khi chạy tool merge deferred JSON vào Excel, tool khử trùng lặp theo email bằng điều kiện:
  ```python
  if em not in dedup or item["written_at"] > dedup[em]["written_at"]:
      dedup[em] = item
  ```
- File sinh sau (Máy B lúc 10:45 hoặc ca chạy sau) có `written_at` lớn hơn file sinh trước (Máy A lúc 09:56) -> Tool chọn nạp file của Máy B vào Excel (Row của Máy B), gạt bỏ file của Máy A.
- Excel chỉ ghi nhận Máy B, để trống dòng của Máy A dù Máy A thực tế đã bị đăng nhập nick đó.

---

## 3 Cơ chế phòng thủ đã chuẩn hóa (2026-09-08)

### 1. Chặn trần 8 tài khoản tại Runtime (`social_reg_v1.py`)
- TikTok giới hạn tối đa 8 tài khoản/máy; khi đủ 8 tài khoản, TikTok ẩn hoàn toàn nút "Thêm tài khoản" (`id/ldd`).
- Khi mở Account Switcher dropdown, script đếm số tài khoản hiện có trên app. Nếu đã đủ 8 nick:
  - Báo trạng thái `MACHINE_FULL_8_ACCOUNTS`.
  - Tự động đóng dropdown, đưa máy về HomeScreen an toàn.
  - Thoát sạch sẽ, tuyệt đối không cố tìm nút "Thêm tài khoản" gây crash `RuntimeError`.

### 2. Selector tên hiển thị ngắn trong Account Switcher
- Trong `social_reg_v1.py`, selector dropdown display name trước đây đặt `(x2 - x1) >= 220`.
- Các nick có tên ngắn (như "Hà", "Vy", "An" với width ~168px) bị bộ lọc bỏ qua -> script nhận diện sai trạng thái dropdown.
- Ngưỡng lọc chuẩn: `(x2 - x1) >= 120`.

### 3. Cố định Sheet `'Tài Khoản'` tại Preflight (`tiktok_target_eligibility.py`)
- CẤM gọi `_active_worksheet(workbook)` vì `active` phụ thuộc vào sheet user mở xem gần nhất trước khi save.
- BẮT BUỘC ưu tiên đọc đích danh sheet `'Tài Khoản'`, chỉ fallback khi sheet không tồn tại.

---

## Quy trình xử lý khi phát hiện lệch tài khoản giữa Excel và Máy
1. **Kiểm tra hiện trường thiết bị:**
   - Dùng ATX JSON-RPC hoặc ADB dump XML màn hình Account Switcher trên cả 2 máy.
   - Trích xuất toàn bộ danh sách username (các node `id/lkp` hoặc `content-desc`).
2. **Đối chiếu:**
   - Nếu máy ghi trên Excel thực tế KHÔNG chứa acc: cập nhật lại Excel ghi đúng máy thực tế đang chứa.
   - Nếu **CẢ 2 MÁY CÙNG CHỨA ACC**: BẮT BUỘC dừng lại và báo cáo User chỉ đạo (thường là đăng xuất khỏi máy đăng nhập nhầm để đưa máy về đúng số lượng slot).
