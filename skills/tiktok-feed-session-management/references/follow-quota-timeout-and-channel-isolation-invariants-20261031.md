# Follow Session Quota, Timeout & Runner-Watchdog Decoupling Invariants (2026-10-31)

## 1. Phân Lập Báo Cáo Tuyệt Đối Theo Kênh (Kỷ Luật Chống Chung Đụng)
- **Quy tắc phân kênh bất biến:**
  - `feed_session_watchdog.py`: BẮT BUỘC chỉ báo cáo số liệu lướt Feed (số máy success/fail, số video vuốt, số tim thả, đọc comment). Gửi về duy nhất nhóm **Tiktok Luot Nuoi Acc** (`-5377611430`). TUYỆT ĐỐI KHÔNG chứa số liệu follow chéo hay upload video.
  - `follow_session_watchdog.py`: BẮT BUỘC chỉ báo cáo số liệu Follow chéo (tổng follow M2/M1, nick nhận follow, máy bị nhả follow, lỗi script/xác minh, nick search not-found). Gửi về duy nhất nhóm **Tiktok Follow** (`-5127276494`).
  - `cron_post_upload_sync.py` & Video Watchdog: Gửi về nhóm **Tiktok video** (`-5435853713`).
- **Phân rã Process Lock trong `lock.py` (`is_feed_runner_active`):**
  - CẤM TUYỆT ĐỐI đưa các pattern của tiến trình upload video/avatar nền (`run_post.py`, `tiktok_workflow`, `tiktok_upload`) vào danh sách nhận diện runner nuôi feed (`runner_patterns`).
  - Lý do: Tác vụ nạp avatar/upload video nền chạy trong khung giờ rảnh (09:30 - 11:30) sẽ kích hoạt cờ `runner_busy = True` giả, làm tê liệt hàm `can_report_session()` khiến toàn bộ báo cáo feed & follow buổi sáng bị câm nín (ngộ nhận feed vẫn đang chạy dở).

## 2. Bản Chất Quota & Trần Nhóm B (Max Volume AB-Test)
- **Quy định trần Nhóm B (Máy Chẵn):**
  - **Trần phiên đơn lẻ:** Cố định cứng `cap = 20 lượt / phiên`. CẤM TUYỆT ĐỐI để thuật toán leo trần động (`active_ceiling`) đẩy trần 1 phiên lên 25–30 lượt kể cả với nick Veteran.
  - **Dải dao động ngẫu nhiên một phiên:** `[cap - 2, cap]` $\implies [18, 20]$ lượt (ngẫu nhiên 18, 19 hoặc 20 lượt).
  - **Tổng trần cả ngày:** 1 ngày 2 phiên $\implies \mathbf{Max\ Daily = 40\ lượt / ngày}$.
- **Trần Cấp Đầu Phiên vs Số Lượt Thực Tế Bấm Được:**
  - Trần $[18, 20]$ là **Hạn mức khống chế trên (Max Cap)**.
  - Số lượt thực tế bấm được phụ thuộc vào số lượng nick hợp lệ trong mỏ Anchor (Module 2) hoặc số nick nợ trong list tìm kiếm (Module 1).
  - Khi cạn mỏ nick hợp lệ, máy chủ động kết thúc phiên ở mức an toàn (ví dụ 16 lượt hoặc 12 lượt) với `status: OK`, không cố bấm vào nick rác hay nick không tồn tại.

## 3. Khống Chế Timeout & Tốc Độ Thực Thi (Module 2 vs Module 1)
- **Tốc độ thực thi theo module:**
  - **Module 2 (Theo Anchor):** Bấm trực tiếp trên list follower + ngâm xem video ngẫu nhiên $\implies$ ~35–45s / lượt. 20 lượt mất ~12–15 phút. Timeout 20 phút (1.200s) là ĐỦ.
  - **Module 1 (Gõ tìm kiếm bù quota):** Swipe feed $\rightarrow$ search icon $\rightarrow$ type UID $\rightarrow$ wait result $\rightarrow$ open profile $\rightarrow$ watch video $\rightarrow$ tap follow $\rightarrow$ pull-to-refresh verify $\rightarrow$ inter-delay (8-25s) $\implies$ ~70–90s / lượt.
- **Nghẽn Timeout khi Fallback:**
  - Nếu Module 2 chỉ ăn được 10-11 lượt (~12 phút), Module 1 chỉ còn 8 phút trước khi chạm `follow_timeout_seconds` (1.200s). Với 8 phút, Module 1 chỉ đủ thời gian gõ tìm kiếm thêm 5 nick là cạn sạch quỹ thời gian và kích hoạt `has_time_for_next_action(reserve_seconds=90s)` để Graceful Exit.
  - Muốn máy vét trọn vẹn trần 20 khi có fallback Module 1: Cần nâng timeout lên **25 phút (1.500s)** HOẶC đảm bảo mỏ Anchor của Module 2 luôn dày ($\ge 300 - 500$ following) để ăn trọn trong Mode 2.
- **Minh bạch hóa lỗi Module 1 lên Watchdog:**
  - Khi Module 1 search không thấy nick (`ID không khớp sau search`), code vẫn tự động thử tiếp nick sau trong danh sách (cho phép tới 5 lần consecutive not found). Tuy nhiên, Watchdog BẮT BUỘC phải trích xuất các nick search not-found này vào báo cáo, không được nuốt chửng khi máy đạt `status: OK`.

## 4. Hạt Sạn Logic Mode 2: Đánh Sập Vòng Lặp Anchor Khi Row Bị Lỗi Verify
- **Hiện tượng (Sự cố M12):** Anchor có hàng trăm follower nhưng sau khi follow được 11 nick liên tiếp, đến nick thứ 12 bị lỗi verify UI sau tap (`MANUAL_REVIEW: verify row sau tap không xác định`), script lập tức gọi nhánh `else: # manual` trong `mode2_follow_followers.py` với `failed = True; break`.
- **Hậu quả:** Lệnh `break` vội vã đánh sập toàn bộ vòng lặp duyệt của Anchor, vứt bỏ hàng trăm nick con còn lại phía sau, ép máy chuyển sang `mode2_degraded` và fallback sang Mode 1 gõ search chậm chạp gây cháy giờ.
- **Quy chuẩn sửa đúng:** Gặp lỗi verify UI trên 1 nick con đơn lẻ $\implies$ Đánh dấu skip nick đó, ghi log warning và TIẾP TỤC cuộn danh sách bấm nick tiếp theo cho tới khi đủ quota hoặc hết danh sách thật sự (`idle_scrolls >= 25`). CẤM `break` đánh sập phiên khi Anchor chưa hết tài nguyên.
