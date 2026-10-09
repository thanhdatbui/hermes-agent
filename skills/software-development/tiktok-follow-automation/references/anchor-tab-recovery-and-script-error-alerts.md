# Khắc Phục Kẹt Mở Tab Anchor (Mode 2) & Quy Chuẩn Cảnh Báo Lỗi Script Hàng Loạt

## 1. Quy Tắc Báo Cáo & Farm Alert (User Invariant)
- **Định danh bằng Nick / Username:**
  - Mọi báo cáo đối soát follow hoặc theo dõi hoạt động farm BẮT BUỘC định danh theo Username / Nick TikTok (`@username`), CẤM chỉ báo cáo chung chung bằng số máy (`M<số>`).
  - Đối soát giữa số liệu script runner (Path B bắt nhả nút) vs số liệu cào Web profile (`tiktok_account_tracker.py` -> SQLite `tiktok_tracker.db` -> Dashboard `:1905`) phải chỉ rõ từng nick cụ thể và mức tăng $\Delta$.
- **Bắt buộc bắn Farm Alert khi lỗi script hàng loạt:**
  - Nếu $\ge 3$ máy (hoặc $\ge 15\%$ batch) gặp lỗi script (kẹt tab Anchor, crash, auth timeout, upload fail): BẮT BUỘC phát cảnh báo đỏ **Farm Alert / Batch Alert** về nhóm Telegram sự cố kèm lý do chi tiết và chỉ định máy Canary.
  - TUYỆT ĐỐI CẤM nuốt lỗi, cấm chỉ in số máy cộc lốc không kèm lý do, hoặc gom lỗi script vào mục "Bỏ qua: Khác" của báo cáo ca thường.

## 2. Bẫy Fatal Break Khi Mở Tab Anchor (Mode 2)
### Triệu chứng:
Toàn farm chỉ kịp follow duy nhất 1 nick Anchor (+1) rồi dừng ca nuôi, dù ngân sách phiên là 10-20 follow. Các nick khác trong safe không được follow, và Mode 1 (Search bù) không bao giờ được kích hoạt.

### Nguyên nhân gốc rễ:
1. **Fatal Break & Manual Review:**
   - Trong `mode2_follow_followers.py` (quanh dòng 1935), khi mở tab "Đang follow" của Anchor thất bại lần 2 sau ladder, code cũ gán `res.status = "MANUAL_REVIEW"` và thực thi `break`.
   - Lệnh `break` này thoát vòng lặp ngay lập tức, bỏ qua mọi anchor còn lại trong hàng đợi.
   - Khi trả về `follow_engine.py`, trạng thái `res.status != STATE_OK` khiến engine bỏ qua luôn bước chạy `run_mode1` (Search Follow bù sau). Kết quả: phiên dừng với đúng 1 follow.
2. **Selector Drift Trên Màn Hình Danh Sách Follower:**
   - `_classify_follower_surface` chỉ kiểm tra danh sách tĩnh `FOLLOWER_LIST_RECYCLER_IDS` (u5r, uo1, uvz...). Khi TikTok update đổi resource ID, hàm coi giao diện là "invalid" và fail.
   - `_following_tab_node` giới hạn tọa độ `y < 550` quá hẹp, khiến trên Samsung S7 dòng chữ "Đang follow" ở `y = 560` bị bỏ qua.

### Giải pháp kỹ thuật đã chuẩn hoá:
1. **Safe-Skip Thay Vì Break:**
   - Khi `_open_following_tab` fail lần 2 trên một anchor: ghi log `logger.warning(...)` và `continue` để chuyển sang anchor tiếp theo.
   - Nếu duyệt hết 3 anchor mà không mở được tab nào, Mode 2 kết thúc với trạng thái `OK` để `follow_engine.py` kích hoạt Mode 1 bù đủ budget 10-20 follow cho phiên.
2. **Fast-path Selector:**
   - Trong `_classify_follower_surface`: kiểm tra thêm class attribute chứa `"RecyclerView"` và sự hiện diện của các item follower (`txt_user_name`, `txt_desc`). Nếu thỏa mãn, trả về ngay `"populated"`.
   - Trong `_following_tab_node`: mở rộng `y < 600` và bổ sung các ID mới (`id/t1i`, `id/t1h`).

## 3. Ngân Sách Follow Hiện Hành (Budget Invariants)
- **Chu kỳ thiết kế:**
  - `budget_per_session_min: 10`, `budget_per_session_max: 20` (random `randint(10, 20)` mỗi phiên cho nick đủ điều kiện).
  - `budget_per_day: 40` (trần tối đa 1 ngày).
- **Bộ lọc an toàn (Dual Gate):**
  - Chỉ nick có $\ge 10$ video đã upload mới được mở tính năng follow chéo.
  - Nick rơi vào chu kỳ Dưỡng sinh 1/3 (Organic Rest) hoặc đang trong cooldown nhả follow 24h sẽ nhận budget = 0.
