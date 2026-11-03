# Bidirectional Reconcile Automation Pattern (Kibe <-> Admin)

## 1. Cơ Chế Cơ Giới Hóa Tự Động 2 Chiều
- **Vị trí script thi công:** `D:/Taadaa/tools/sync_2fa_to_admin.py`
- **Host chạy Cron:** Kibe Controller (điều phối trung tâm qua SSH LAN tới Admin-PC `192.168.110.119`).
- **Hook Cronjob:** `hourly-stale-post-receipts-reconcile` (ID: `8d6b3c18dd64`), lịch chạy phút 20 mỗi giờ (`20 * * * *`).

## 2. Luồng Thực Thi Chi Tiết

### Chiều 1: Admin -> Kibe (`reconcile_pull()`)
- Mục tiêu: Kéo tài khoản dải `machine_id >= 200` có `twofa_secret` hoặc `password` mới từ Admin về Kibe.
- Cách thức: Gọi lệnh qua SSH:
  ```bash
  python D:/Taadaa/tools/admin_ssh.py "python D:/Taadaa/tools/farm_db.py query \"SELECT username, password, twofa_secret FROM tiktok_accounts WHERE machine_id >= 200 AND length(twofa_secret) > 5\""
  ```
- Phân tích output dạng pipe `|` và chạy `UPDATE tiktok_accounts SET twofa_secret = ?, password = ? WHERE username = ?` vào database `D:/Taadaa/data/farm_master.db` trên Kibe.

### Chiều 2: Kibe -> Admin (`reconcile_push()`)
- Mục tiêu: Đẩy tài khoản dải `machine_id <= 80` có cập nhật từ Kibe sang Admin.
- Cơ chế O(1) Diff (Chống spam SSH):
  1. Truy vấn nhanh danh sách 2FA/Password dải `<= 80` hiện có trên Admin.
  2. So khớp với dữ liệu trên Kibe.
  3. Nếu không có lệch: In `Up to date` và kết thúc ngay ($O(1)$ calls).
  4. Nếu có lệch: Chỉ phát lệnh `UPDATE` cho đúng các tài khoản có diff.

## 3. Bài Học & Pitfalls Thực Tế
- **Cấm dừng ở Sync 1 Lần Bằng Tay:** Khi User hỏi "đã có cron tự sync chưa", câu trả lời phải là cơ chế tự động định kỳ (Cronjob), không được lấy kết quả của lệnh chạy thủ công 1 lần để báo là "xong rồi".
- **Bắt buộc 2 chiều đối xứng:** Đã là mô hình Full-Farm Replica thì phải có cả chiều kéo (Admin -> Kibe) và chiều đẩy (Kibe -> Admin). Thiếu 1 chiều là rủi ro split-brain khi cụm còn lại có cập nhật mới.
- **Pipeline `--allow-no-test`:** Khi sửa script sync nội bộ qua `unified_patch_pipeline.py`, nếu task không có test delta trong thư mục `tests/`, phải truyền cờ `--allow-no-test` để vượt qua `MANDATORY_TEST_DELTA_VIOLATION`.
