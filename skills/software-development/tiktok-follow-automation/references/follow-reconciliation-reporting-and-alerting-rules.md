# Quy Tắc Đối Soát Follow, Định Danh Tài Khoản & Bắn Cảnh Báo Lỗi Script Hàng Loạt

## 1. Định Danh Báo Cáo Theo Tài Khoản (User Preference Bắt Buộc)
- **Quy tắc cốt lõi:** Mọi báo cáo đối soát Follow hoặc tình trạng Farm BẮT BUỘC định danh theo Username / Nick TikTok cụ thể (kèm slot Row / Máy, ví dụ: `@thy.dung1828 (Row 1 - M38)`).
- **CẤM TUYỆT ĐỐI:** Báo cáo cộc lốc chung chung chỉ có số máy (ví dụ "Máy 38 tăng 18 lượt"). Nick TikTok là tài sản định danh cao nhất của Farm.
- **Phân định rõ 2 loại số liệu biến động Following:**
  1. *Số luỹ kế nhiều ngày:* Tổng biến động trong dải ngày dài (ví dụ: từ 19/09 đến 24/09 nick tăng +18 lượt).
  2. *Biến động 24h trên Dashboard `:1905`:* So sánh snapshot lúc 07:00 sáng hôm nay với 07:00 sáng hôm qua (`substr(timestamp, 1, 10) < max_dt`). Chia trung bình mỗi ngày nick tăng từ +1 đến +3 lượt.
  - Phải giải thích rõ khi người dùng thắc mắc về độ lệch giữa Dashboard hàng ngày và số liệu luỹ kế.

---

## 2. HARD INVARIANT: Bắt Buộc Bắn Farm Alert Khi Lỗi Script Hàng Loạt
- **Precedence:** TỐI CAO — Thắng mọi cơ chế làm tròn báo cáo ca.
- **Phạm vi áp dụng:** Áp dụng cho TOÀN BỘ các bước tự động hóa (cả Follow Hook, Upload Video Hook và Lướt Feed).
- **Ngưỡng kép (Dual-Threshold Systemic Alert):**
  - Khi có $\ge 3$ máy (hoặc $\ge 15\%$ số máy trong ca) dính lỗi script:
    + Follow Hook: `MANUAL_REVIEW`, `FOLLOW_FAILED`, crash, timeout mở tab.
    + Upload Hook: `error`, `timeout`, thiếu hook, crash uploader.
  - **Hành động bắt buộc:**
    1. BẮT BUỘC bắn tin nhắn cảnh báo khẩn cấp `🚨 [FARM ALERT / BATCH ALERT: LỖI HỆ THỐNG]` về nhóm Farm Alert Telegram (`-5373649734`).
    2. Nêu rõ nguyên nhân gốc rễ cụ thể (ví dụ: *Kẹt mở tab Đang follow do lệch selector / mạng lag* hoặc *Uploader timeout sau 20 phút*).
    3. Cung cấp ngay lệnh Canary 1 máy đại diện để kiểm chứng: `python D:/Taadaa/tools/inspect_machine.py <M>`.
- **CẤM TUYỆT ĐỐI:**
  - CẤM nuốt lỗi script hàng loạt để ngụy trang thành báo cáo ca nuôi bình thường `📊 [TIKTOK NUÔI ACC] Ca X hoàn tất`.
  - CẤM gom lỗi script vào mục `Bỏ qua: Khác`.
  - CẤM chỉ in danh sách số máy cộc lốc (ví dụ `Lỗi script/xác minh (2): 32, 48`) mà không in kèm lý do lỗi cụ thể.

---

## 3. Kiến Trúc Budget Follow & Cơ Chế Chống Kẹt Mở Tab Anchor (Hybrid Mode)
- **Lịch sử thiết kế ngân sách Follow:**
  + Gốc ban đầu: 3 – 5 follow / phiên (trần ngày 10).
  + Giai đoạn 16/08 – 09/09: 6 – 10 follow / phiên (trần ngày 25).
  + Giai đoạn 09/09 – 15/09: 15 – 18 follow / phiên (trần ngày 35).
  + **Hiện hành (từ 16/09):** **10 – 20 follow / phiên** (`randint(10, 20)`), trần ngày 40 (`budget_per_day: 40`).
- **Cơ chế Hybrid Mode chuẩn:**
  + Chạy Mode 2 (Anchor) trước để khai thác danh sách Following của các nick nội bộ.
  + Nếu Anchor hết nick hoặc bị lỗi $\rightarrow$ Mode 1 (Search Follow) BÙ SAU để đạt đủ budget 10 – 20 follow cho phiên.
- **Bẫy chí tử cần tránh (Mode 2 Fatal Break Trap):**
  + Khi `_open_following_tab` thất bại lần 2 trên một Anchor: TUYỆT ĐỐI CẤM gán `res.status = "MANUAL_REVIEW"` và `break` làm dừng phiên. Điều này khiến `follow_engine.py` hủy bỏ luôn Mode 1 (Search bù), làm máy chỉ kịp follow 1 lượt Anchor rồi bỏ phí toàn bộ budget!
  + **Quy chuẩn sửa đổi:** Bắt buộc dùng `logger.warning(...)` và `continue` (safe-skip sang Anchor kế tiếp), hoặc kết thúc Mode 2 trong trạng thái `OK` để Mode 1 tự động tiếp quản tìm nick follow bù.
- **Bảo vệ Selector chống Drift TikTok mới (47.0.3+):**
  + `_classify_follower_surface`: Phải có fast-path kiểm tra thuộc tính class `RecyclerView` kết hợp sự hiện diện của item username/desc (`:id/txt_user_name`, `:id/txt_desc`), không được phụ thuộc duy nhất vào danh sách resource-id obfuscated cố định.
  + `_following_tab_node`: Mở rộng ngưỡng tọa độ $y < 600$ (trên Samsung S7 dòng tab có thể nằm ở $y=560$) và bổ sung các ID mới (`id/t1i`, `id/t1h`).
