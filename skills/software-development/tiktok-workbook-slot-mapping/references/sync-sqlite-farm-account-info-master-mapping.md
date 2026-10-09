# Đồng Bộ SQLite farm_account_info Chuẩn Từ File Tổng Master (Source of Truth)

## 1. Nguyên Tắc Cốt Lõi & Source of Truth (SOT)
- **Source of Truth duy nhất**: File tổng **`taikhoan_dat_v2_updated .xlsx`** tại:
  - Cụm Kibe (Máy 1–80): `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`
  - Cụm Admin (Máy 201–280): `D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx`
- **Database SQLite**: `D:/Taadaa/data/tiktok_tracker.db` chứa bảng `farm_account_info (username, may, tik, host_id, updated_at)`.
- **Vai trò của `farm_account_info`**:
  - Cung cấp mapping (Máy, Tik, Host) cho Dashboard Farm (`http://localhost:1905`).
  - Cung cấp danh sách tài khoản theo máy và ca cho Watchdog (`post_evening_avatar_watchdog.py`) và daily crawler.
- **BẢN CHẤT QUY TẮC MAPPING**:
  Toàn bộ hệ thống Phone Farm phân bổ slot theo công thức toán học bất di bất dịch:
  $$\text{Tik (Slot)} = ((\text{Folder Video} - 1) \pmod 8) + 1$$
  $$\text{Máy} = \text{Cột Máy trong file Master (row[0])}$$
  $$\text{Host ID} = \text{'kibe' nếu Máy } \le 80 \text{ else 'admin'}$$

## 2. Căn Nguyên Gốc Rễ Khi Bị Lệch Dashboard (Desync)
- **Hiện tượng**: User thấy trên Dashboard hiển thị badge `M69 · T8`, nhưng trên file `Tik7.xlsx` dòng 69 lại ghi nick đó, trong khi `Tik8.xlsx` dòng 69 là nick khác. User hỏi: *"Ủa trên này ghi Tik 8 mà sao lại ở Tik 7?"* và *"Thế phải sửa hết mapping của sqlite lại chứ, đáng lẽ map theo file tổng taikhoandatv2 chứ"*.
- **Nguyên nhân**:
  1. File Excel Master `taikhoan_dat_v2_updated .xlsx` **KHÔNG BAO GIỜ tráo đổi**.
  2. Database `farm_account_info` bị lệch do lịch sử các lần import/crawl cũ ghi nhận theo **thứ tự thời gian xuất hiện** (ví dụ: máy có 7 nick từ trước, sau đó reg thêm nick thứ 8 thì script cũ gán nick mới vào slot 8 thay vì tính theo STT $\pmod 8$).
  3. Hoặc do script sync trước đây đọc từ các file riêng lẻ (`taikhoan_run_safe.xlsx`) thay vì đọc từ File Tổng Master.

## 3. Lệnh Đồng Bộ Chuẩn 1 Chạm (Standard Tool)
Đã đóng gói script chuẩn tại:
`D:/Taadaa/tools/sync_farm_account_info.py`

### Cách thực thi:
```bash
python D:/Taadaa/tools/sync_farm_account_info.py
```

### Cơ chế an toàn tự động:
1. **Tự động sao lưu DB trước khi ghi**: Sinh bản backup nguyên vẹn `D:/Taadaa/data/tiktok_tracker.db.bak_sync_<timestamp>`.
2. **Quét sạch cả 2 file Master**: Đọc `Tài Khoản` của cả Kibe và Admin.
3. **Áp dụng chuẩn công thức $\text{Tik} = ((\text{Folder}-1) \pmod 8) + 1$**: Đảm bảo 100% tài khoản khớp slot.
4. **Upsert chuẩn SQLite (`ON CONFLICT(username) DO UPDATE`)**: Cập nhật lại `may`, `tik`, `host_id`, `updated_at` mà không làm mất liên kết khóa ngoại.
5. **In telemetry kiểm tra**: Đếm tổng số nick nạp từ Kibe, Admin và tổng số nick trong DB (thường ~1.250 nick).

## 4. Kiểm Chứng Sau Đồng Bộ (Verification Protocol)
Sau khi chạy script sync, bắt buộc kiểm tra nhanh:
1. Số tài khoản LIVE bị thiếu thông tin máy/tik trên DB:
   ```sql
   WITH Latest AS (
       SELECT username, status, ROW_NUMBER() OVER (PARTITION BY username ORDER BY timestamp DESC) as rn
       FROM snapshots
   )
   SELECT COUNT(*) FROM Latest
   WHERE rn = 1 AND status = 'LIVE' AND username NOT IN (SELECT username FROM farm_account_info);
   -- Kỳ vọng: 0
   ```
2. Kiểm tra tài khoản cụ thể bị nghi vấn:
   ```sql
   SELECT username, may, tik, host_id, updated_at FROM farm_account_info WHERE username = '<target_username>';
   ```
3. F5 lại Dashboard tại `http://localhost:1905` để xác nhận badge `M{may} · T{tik}` đã hiển thị chính xác.
