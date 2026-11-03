# Distributed SQLite SSOT Reconciliation Architecture (Dual-Cluster Kibe vs. Admin)

## 1. Bản chất kiến trúc sổ cái phân tán (Ground Truth)
- **Kibe (Máy 1–80)** và **Admin (Máy 201–280)** sở hữu dải thiết bị và tài khoản độc lập tuyệt đối (`ZERO_DATA_OVERLAP`).
- Khi Kibe SSH sang Admin để kích hoạt các runner/watchdog (như 2FA đêm, feed session, avatar):
  + Tiến trình Python thực thi trên CPU của Admin và đọc/ghi $O(1)$ vào file SQLite cục bộ của Admin: `admin-farm:D:/Taadaa/data/farm_master.db`.
  + File SQLite trên Admin là **sổ cái sống tại hiện trường của cụm Admin**. Kết quả cập nhật (password mới, 2FA secret mới) nằm ngay tại Admin.
  + **Tự chủ khi Failover:** Nếu máy Kibe bị sập nguồn, cháy máy, mất điện, máy Admin **hoàn toàn độc lập**, không mất bất kỳ bản ghi nào và tự vận hành 80 máy của nó tại chỗ mà không cần Kibe.

## 2. Điểm mù đồng bộ (The Sync Drift Pitfall)
- **Lệch trạng thái (State Drift):** Sau khi batch trên Admin hoàn thành, dữ liệu mới nằm ở `admin-farm:farm_master.db`, nhưng `kibe:farm_master.db` vẫn giữ dữ liệu cũ nếu không có cơ chế kéo về.
- **Bẫy tư duy lôi lại Excel:** Tuyệt đối **CẤM** dùng Excel làm cầu nối trung gian để đồng bộ lại SQLite (ví dụ: tạo cron scheduler đọc Excel OneDrive rồi rebuild SQLite). Khi đã chuyển sang SQLite SSOT, Excel hoàn toàn bị loại bỏ khỏi runtime; mọi sync phải là **SQLite <-> SQLite direct sync**.

## 3. Quy chuẩn đồng bộ ngược (Reconcile Pull Pattern)
- Sau khi lệnh SSH kích hoạt batch trên Admin kết thúc, hoặc định kỳ mỗi ca, máy Kibe (Controller) thực hiện đúng 1 truy vấn đối soát nhẹ qua SSH:
  ```powershell
  python D:/Taadaa/tools/farm_db.py query "SELECT username, password, twofa_secret FROM tiktok_accounts WHERE machine_id >= 200 AND (twofa_secret IS NOT NULL OR password IS NOT NULL)"
  ```
- Kibe đọc stdout và chạy transaction update vào `D:/Taadaa/data/farm_master.db` trên Kibe:
  ```sql
  UPDATE tiktok_accounts SET twofa_secret = :twofa_secret, password = :password WHERE username = :username;
  ```
- Thời gian thực thi: Chỉ mất ~1.5 - 2.5s qua SSH mạng LAN, không truyền file nhị phân lớn, không nghẽn buffer PowerShell.

## 4. Kỷ luật giao tiếp với User (Anti-Bullshit & Action-First)
- Khi user hỏi trạng thái ("Tất cả xài SQLite chưa?", "Dữ liệu được sync chưa?"):
  + BẮT BUỘC trả lời thẳng: **CÓ hay CHƯA**, số lượng bản ghi cụ thể, tỷ lệ % hoàn tất.
  + TUYỆT ĐỐI KHÔNG lải nhải giải thích lý do, không vòng vo kỹ thuật khi chưa trả lời câu hỏi chính.
  + Trả lời câu hỏi trước, đưa bằng chứng (Read-back proof từ database) ngay sau đó.
