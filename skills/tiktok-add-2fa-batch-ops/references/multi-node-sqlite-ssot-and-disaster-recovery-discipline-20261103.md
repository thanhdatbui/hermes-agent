# Multi-Node SQLite SSOT & Disaster Recovery Discipline (2026-11-03)

## 1. Bối cảnh & Hiện trạng
- **Mục tiêu hệ thống:** Vận hành trơn tru hàng ngày giữa cụm Kibe (Máy 1–80) và cụm Admin (Máy 201–280) không nghẽn lock, đồng thời bảo đảm Disaster Recovery (DR): nếu máy Kibe cháy/hỏng phần cứng thì toàn bộ 80 máy S7 của Kibe cắm sang máy Admin vẫn có đủ 100% dữ liệu để chạy tiếp ngay lập tức.
- **Sự cố thực tế:**
  1. Khi Kibe SSH sang Admin chạy batch 2FA, runner trên Admin ghi trực tiếp vào `admin:D:/Taadaa/data/farm_master.db`. Sau khi xong batch, Kibe thiếu bước Reconcile Pull, dẫn đến việc Admin có 251 tài khoản có 2FA trong khi Kibe chỉ có 202 tài khoản (lệch đúng 49 tài khoản).
  2. Tư duy sai lầm tạo Scheduled Task đọc lại từ Excel để sync sang SQLite gây xung đột và đi ngược lại nguyên tắc loại bỏ bóng ma Excel trong runtime.

## 2. Kiến Trúc Đồng Bộ Được Hội Đồng Cố Vấn (Council) Thống Nhất
Mô hình chuẩn hóa: **Full-Farm Replica + Single-Writer Partition + Row-Level Upsert + Dual-Trigger Reconcile**.

1. **Full-Farm Replica:** Cả 2 máy Kibe và Admin đều lưu giữ bản đầy đủ 100% của 1.270 tài khoản TikTok, 1.487 mailboxes, 246 máy trong `D:/Taadaa/data/farm_master.db`.
2. **Single-Writer Partition (Phân quyền ghi độc quyền):**
   - Kibe độc quyền ghi dải máy `1 đến 80`.
   - Admin độc quyền ghi dải máy `201 đến 280`.
   - CẤM TUYỆT ĐỐI ghi chéo ranh giới để triệt tiêu 100% nguy cơ tranh chấp ghi (Write Contention) và Split-Brain.
3. **Kỷ luật đồng bộ cấp dòng (Row-Level Upsert, CẤM chép đè file `.db`):**
   - Tuyệt đối không copy đè nguyên file `.db` qua mạng LAN vì dễ gây mất dữ liệu dở dang hoặc lấy snapshot cũ đè snapshot mới.
   - Đồng bộ chỉ chuyển các trường thay đổi (`password`, `twofa_secret`, `updated_at`) qua câu lệnh SQL an toàn:
     ```sql
     UPDATE tiktok_accounts SET twofa_secret = ?, password = ? WHERE username = ?;
     ```
4. **Dual-Trigger Reconcile:**
   - *Event-driven:* Ngay sau khi lệnh SSH từ Kibe sang Admin kết thúc, script điều phối tự động kéo kết quả dải máy >= 200 về Master Kibe (mất ~1.5s qua SSH).
   - *Time-driven:* Định kỳ đối soát chéo số lượng bản ghi giữa 2 máy để bù đắp các dòng bị sót.

## 3. Kỷ luật Thực thi & Quy tắc Ứng xử với Người dùng
1. **Loại bỏ triệt để bóng ma Excel:** CẤM tạo các script/task đọc ngược Excel để sync hay rebuild SQLite trong runtime. Excel chỉ là mirror xem báo cáo.
2. **Kỷ luật Timeout Terminal (Gate G15):** Mọi lệnh terminal gọi `consult_advisor.py`, `gate_b_planner.py` hoặc Claude CLI / Worker BẮT BUỘC có tham số `timeout >= 300s`. Không tự tiện hạ timeout thấp (60s/120s) làm ngắt ngang phân tích.
3. **Giao tiếp trực diện, cấm lải nhải ngụy biện:** Khi người dùng hỏi ngắn gọn ("xong chưa", "sync chưa"), trả lời thẳng thắn "Đã xong" hoặc "Chưa xong" kèm số liệu định lượng thật, cấm dùng lý do ngắt mạng giả tạo để ngụy biện cho lỗi thuật toán/timeout.
