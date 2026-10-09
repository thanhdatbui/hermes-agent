# Kiến Trúc Mô Phỏng Hành Vi & Chống Phát Hiện Bot Trên TikTok Farm (Human-like Fidelity 9.0/10)

## 1. Tầng Cảm Ứng & Cử Chỉ (Touch & Gesture Layer)
- **Xóa bỏ triệt để chữ ký đường thẳng nhân tạo $dx = 0$:**
  - `start_x`: Chọn ngẫu nhiên trong khoảng `[465, 525]`.
  - `end_x`: Lệch nghiêng tự nhiên $\Delta X \in [-18, +12]\text{px}$ (mô phỏng góc vung bán kính ngón tay cái người thật).
  - Hành lang an toàn tâm màn hình: Kẹp chặt cả `start_x` và `end_x` trong khoảng `[450, 540]` trên màn hình 1080p. Cách xa mép Camera Story ($0 \sim 150\text{px}$) và Profile ($930 \sim 1080\text{px}$) trên $300\text{px}$.
  - **Skew Fallback (Phòng thủ tham số lệch):** Nếu tham số truyền vào bị lệch nguy hiểm ($|\Delta X| > 30\text{px}$), hệ thống tự động ép thẳng đứng $start\_x = end\_x$ để triệt tiêu nguy cơ trượt nhầm màn hình.
  - **Cử chỉ vuốt ngược (Downward / Rewind Swipe):** Bắt buộc phải cô lập sau cờ `allow_downward=True`. Mọi caller vuốt feed thông thường mặc định vẫn duy trì invariant vuốt lên (`start_y > end_y`).
- **Lưới Video Profile (Upload Engine):**
  - Trong `adapter.py`, các thao tác restore swipe và grid scroll swipe áp dụng `drift_x = start_x + random.randint(-15, 12)` và thời lượng vuốt ngẫu nhiên `420ms - 490ms` (thay vì 450ms tĩnh).

---

## 2. Tầng Độ Hỗn Loạn Tương Tác (Behavioral Entropy Layer)
- **Phân tầng tỷ lệ Like theo từng phiên:**
  - Tab Đang Follow: Biến thiên ngẫu nhiên `30% - 60%` mỗi phiên.
  - Tab Bạn bè: Biến thiên ngẫu nhiên `50% - 80%` mỗi phiên.
  - Tab Đề xuất (For You): `8%` (hoặc `20%` tại nhịp Deep Inspect).
- **Tương tác Lưu vào Yêu thích (Bookmark / Favorite):**
  - *Bookmark sau Like:* Tỷ lệ `15% - 30%` sau khi thả tim thành công, nghỉ ngâm `0.8s - 1.8s` rồi mới tap Lưu.
  - *Bookmark độc lập (không cần Like):* Tỷ lệ `3% - 5%` trên các video không like hoặc like bị lỗi/đã like từ trước. Phá vỡ tương quan cứng $Like \rightarrow Save$. Bắt buộc kiểm tra `x >= 750` và kết quả ADB fail-closed (`res.ok is True`).
- **Xem lướt Bình luận (Comment Peek):**
  - Tỷ lệ `12%` độc quyền trên video Deep Inspect.
  - Mở sheet bình luận bên phải (`x >= 750`), ngâm đọc `2.0s - 4.0s` (có 50% xác suất cuộn nhẹ 1 nhịp 300ms đọc tiếp `1.0s - 2.0s`).
  - Đóng sheet bằng phím Back (`KEYCODE_BACK`), nghỉ `0.6s - 1.2s`.
  - **Closed-loop Verification (Fail-closed):** Kiểm tra activity/package sau khi đóng sheet. Nếu mất focus TikTok hoặc gặp exception, log `failed_dismissal` và trả về `False`, tuyệt đối không dùng `except Exception: pass` nuốt lỗi.
- **Nhịp vuốt ngược xem lại video (Rewind Swipe - Session Narrative):**
  - Tỷ lệ `5% - 8%` từ video thứ 3 trở đi (trừ video cuối ca).
  - Vuốt ngược `[sx, 480] -> [ex, 1380]`, ngâm xem lại `2.0s - 4.0s` rồi mới tiếp tục lướt xuôi.
  - Tạo ra "câu chuyện xao nhãng" tự nhiên của người dùng thật.
- **Phân nhánh Thẻ Đề Xuất Follow lại trên Feed:**
  - Nick sạch: Tự động tap "Follow lại" để tăng tương tác 2 chiều.
  - Nick dính cờ cooldown nhả follow: Tự động tap "Không quan tâm" để tránh bị phạt dồn.

---

## 3. Tầng Nhịp Độ & Điều Phối (Pacing & Cadence Layer)
- **Follow Engine (`tiktok-follow`):**
  - Dwell time ngâm Profile mục tiêu: `6.0s - 12.0s` ngẫu nhiên trước khi tap nút Follow.
  - Post-tap delay: Chờ server phản hồi `2.5s - 5.0s` ngẫu nhiên.
  - Inter-follow delay: Giãn cách `8.0s - 25.0s` giữa 2 lượt follow.
- **Upload Engine (`Tiktok-video`):**
  - Dwell Time ngâm trước khi Đăng: Sau khi điền caption/hashtag và ghi nhận post intent hợp lệ, ngâm dừng `1.8s - 3.5s` trước khi tap nút "Đăng" (chống cờ Automated Instant Posting).
  - Giới hạn Hook Upload: Chỉ phiên 2 (phiên kết thúc ca) mới được kích hoạt upload video, bảo toàn kho video trong thời gian ngâm án phạt.
- **Cron Điều Phối Farm (Anti-Clustering):**
  - 4 Ca x 2 Phiên / ngày, Dead Zone `02:30 -> 05:59` sáng hạ nhiệt thiết bị.
  - Phân chia ngày chẵn/lẻ: 8 nick/máy $\rightarrow$ mỗi ngày chỉ chạy 4 nick (1 ca/nick, nghỉ 24h).
  - Throttling 40 workers song song trên pool 160 máy.
  - Khởi động so le (Machine Start Stagger): Trễ `2.000ms - 8.000ms` giữa các máy.
  - Xáo trộn thứ tự máy (`--randomize-machine-order`) mỗi ca.
