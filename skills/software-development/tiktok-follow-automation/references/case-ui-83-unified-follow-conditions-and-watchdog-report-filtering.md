# Case UI-83: Thống Nhất Điều Kiện Follow Tự Nhiên & Chéo (Dual Gate) và Lọc Báo Cáo Đối Soát Watchdog

**Ngày ghi nhận:** 2026-10-02  
**Chỉ đạo User:** 
1. Follow tự nhiên cứ theo cơ chế follow chéo là xong (cooldown/chưa đủ điều kiện thì tự nhiên cũng không được follow).
2. Mấy nick không lệch đừng báo vào report watchdog.

---

## 1. Bản Chất Vấn Đề
- Khi chạy Ca 4 Phiên 2 Row 8:
  + M51 (`@sweatfbsxdj`, tạo 16/09, 16 ngày tuổi, 6 video) và M63 (`@nhumai1595`, tạo 16/09, 16 ngày tuổi, 6 video).
  + Follow chéo: Chặn `budget = 0` do Dual Gate yêu cầu `account_age_days >= 21` VÀ `video_count >= 6`.
  + Follow tự nhiên trong lướt feed: Code cũ chỉ check `video_count >= 6` mà không check `account_age_days`, nên vẫn roll 5% follow tự nhiên trên tab For You (M51 bấm 3 nick, M63 bấm 1 nick). Tuy nhiên do nick quá non, server TikTok hủy bỏ tương tác ngầm -> Web đối soát ghi nhận +0, gây ra lệch -3 và -1.
  + Đồng thời, M19 không bị lệch (`diff == 0`) nhưng watchdog vẫn liệt kê chi tiết dòng `KHỚP; chênh lệch +0` làm rối mắt.

---

## 2. Quy Tắc Single Source of Truth Cho Mọi Hành Vi Follow
- Mọi hành vi follow (dù là Follow Tự Nhiên khi lướt feed hay Follow Chéo sau feed) BẮT BUỘC dùng chung MỘT bộ điều kiện Dual Gate:
  1. `is_organic_rest`: Ngày dưỡng sinh -> 0 follow (tự nhiên = 0, chéo = 0).
  2. `is_account_in_follow_cooldown`: Đang bị cooldown phạt nhả follow -> 0 follow (tự nhiên = 0, chéo = 0).
  3. `account_age_days < 21` hoặc `video_count < 6`: Chưa đủ tuổi hoặc chưa đủ 6 video -> 0 follow (tự nhiên = 0, chéo = 0).
- Bất kỳ điều kiện nào khiến nick không đủ tiêu chuẩn đi follow chéo thì BẮT BUỘC PHẢI KHÓA LUÔN cả follow tự nhiên khi lướt feed (`_follow_rate = 0`).

---

## 3. Kỷ Luật Đối Soát Báo Cáo Watchdog
- Trong bảng "Đối soát TikTok Web" (`reconcile_cluster_following`):
  + Nếu `diff == 0` (web tăng đúng bằng script báo / khớp 100%): CẤM in dòng chi tiết nick đó.
  + CHỈ in các nick có `diff != 0` (lệch thật) hoặc gặp lỗi đọc snapshot / UNPROVEN.
