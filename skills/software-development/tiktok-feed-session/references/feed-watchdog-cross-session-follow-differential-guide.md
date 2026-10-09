# Case Feed-Watchdog: Giải Mã Chênh Lệch List Máy Nhả Follow Giữa Các Phiên Trong Cùng Ca

## 1. Hiện Tượng (06/10/2026)
User thắc mắc sau khi nhận báo cáo từ `tiktok-feed-session-watchdog`:
*Cùng 1 ca chạy của 1 row (Row 6), tại sao ở Phiên 1 danh sách máy nhả follow liền lại khác hoàn toàn Phiên 2?*
- Phiên 1 (18:01): Báo 10 máy nhả (`M3, M23, M25, M35, M53, M55, M61, M65, M69, M76`).
- Phiên 2 (20:00): Báo 9 máy nhả (`M5, M17, M40, M44, M46, M58, M62, M70, M78`).

## 2. Invariants & Cấm Kỵ Phán Đoán
- **INVARIANT DƯỠNG SINH (ORGANIC REST):** Dưỡng sinh tính cố định theo NGÀY qua công thức băm MD5 `hashlib.md5(f"{date_str}:{machine}:{row}").hexdigest() % 3 == 0`. Cả 2 phiên trong cùng một ngày BẮT BUỘC có danh sách máy dưỡng sinh giống hệt nhau (~33% máy). CẤM TUYỆT ĐỐI ngụy biện "dưỡng sinh đổi lịch giữa phiên 1 và phiên 2".
- **INVARIANT COOLDOWN PHẠT NHẢ FOLLOW:** Khi một máy bị `FOLLOW_FAILED` (nhả follow liền), hệ thống kích hoạt Fail-Closed và gán Progressive Cooldown (3 ngày). Máy bị phạt ở Phiên 1 BẮT BUỘC bị Cooldown Gate khóa ở Phiên 2 (`follow-released-daily-cooldown`), không bao giờ được chạy follow tiếp trong ca.

## 3. Bản Chất Kỹ Thuật Khi List Nhả Khác Nhau Giữa 2 Phiên
1. **Máy nhả ở Phiên 1 biến mất ở Phiên 2:**
   - Phiên 1: Máy $\ge 6$ video chạy follow và bị nhả $\rightarrow$ dính Progressive Cooldown.
   - Phiên 2: `_run_follow_hook` kiểm tra `_is_account_follow_cooldown()` $\rightarrow$ Skip ngay với lý do `follow-released-daily-cooldown`. Vì không chạy follow nên Phiên 2 không thể bị nhả tiếp, mà rơi vào nhóm `Bỏ qua: Khác`.
2. **Máy mới xuất hiện trong list nhả ở Phiên 2:**
   - Phiên 1: Các máy này có ban đầu đúng **5 video** $\rightarrow$ bị Dual Gate chặn (`under-6-videos-follow-disabled`), hoàn toàn không được chạy follow.
   - Giữa 2 phiên: Trong chính Phiên 1, module **Đăng Video** upload thành công 1 clip mới lên kênh $\rightarrow$ `video_count` nhảy từ 5 lên 6.
   - Phiên 2: Máy đã đủ $\ge 6$ video $\rightarrow$ Dual Gate mở cho chạy follow lần đầu tiên trong ngày $\rightarrow$ gặp TikTok siết nhả anchor và bị tính vào list nhả của Phiên 2.

## 4. Checklist Trích Xuất Hiện Trường O(1)
- `log.jsonl` (dòng đầu): So sánh `extra["video_count"]` giữa P1 và P2 (từ 5 lên 6).
- `upload_result.json` (P1): Kiểm tra máy có upload thành công video mới trong ca không.
- `follow_result.json` (P1 vs P2): Đối soát `under-6-videos-follow-disabled` (P1) $\rightarrow$ `FOLLOW_FAILED` (P2), và `FOLLOW_FAILED` (P1) $\rightarrow$ `follow-released-daily-cooldown` (P2).
