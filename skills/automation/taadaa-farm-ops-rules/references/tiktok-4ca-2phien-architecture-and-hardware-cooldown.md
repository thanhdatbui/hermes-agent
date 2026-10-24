# [DEPRECATED / SUPERSEDED] Kiến Trúc Nuôi TikTok 4 Ca x 2 Phiên Cũ (09/09/2026)

> ⚠️ **CẢNH BÁO LỊCH CŨ ĐÃ HẾT HIỆU LỰC:** Lịch 4 Ca (có Ca 4 lúc 00:00 - 01:30 đêm) đã bị bãi bỏ hoàn toàn từ ngày 11/10/2026.
> **Lịch chuẩn hiện tại là Chu kỳ 4 ngày x 3 Ca / ngày (BỎ HOÀN TOÀN CA 0H ĐÊM):**
> - Ca 1 (Sáng): 06:00 (P1) & 08:00 (P2)
> - Ca 2 (Trưa): 12:00 (P1) & 14:00 (P2)
> - Ca 3 (Tối):  18:00 (P1) & 20:00 (P2)
> - Dead Zone: 21:30 - 05:59 sáng (nghỉ hoàn toàn, hạ nhiệt S7, dọn cache 03:00 - 04:30).

---

## 1. Kiến Trúc 4 Ca x 2 Phiên Cũ (LƯU TRỮ LỊCH SỬ)

### A. Phân Bổ Mốc Giờ (BLOCK_ANCHORS)
- **4 Ca rải đều 6 tiếng/ca (từ 06:00 sáng đến 02:00 đêm):**
  - **Ca 1:** `06:00` (Phiên 1: 06:00 - 07:30, Phiên 2: 07:30 - 10:00)
  - **Ca 2:** `12:00` (Phiên 1: 12:00 - 13:30, Phiên 2: 13:30 - 16:00)
  - **Ca 3:** `18:00` (Phiên 1: 18:00 - 19:30, Phiên 2: 19:30 - 22:00)
  - **Ca 4:** `00:00` (Phiên 1: 00:00 - 01:15, Phiên 2: 01:15 - 03:00)
- **Khoảng trống bảo trì ban đêm:**
  - `03:00 - 06:00`: Toàn bộ máy nghỉ sâu, nhường slot cho `end-of-day-clear-tiktok-cache` (04:00 sáng) và các batch bảo trì.

### B. Quy Hoạch Row Theo Ngày Chẵn / Lẻ (Lanes)
- **Ngày Lẻ (Lane B):** Row 1 (Ca 1), Row 3 (Ca 2), Row 5 (Ca 3), Row 7 (Ca 4).
- **Ngày Chẵn (Lane A):** Row 2 (Ca 1), Row 4 (Ca 2), Row 6 (Ca 3), Row 8 (Ca 4).
- **Quy tắc sở hữu đơn:** Mỗi account chỉ xuất hiện ở đúng 1 Block trong ngày (không còn cơ chế chạy 2 lần/ngày sáng-tối). `max_accounts_per_machine_day: 4`.

---

## 2. Rút Gọn Phiên & Phân Bổ Lại Hook

### A. Rút Gọn Từ 3 Phiên Xuống 2 Phiên/Ca
- Trước đây: 3 phiên x 35-40p = ~105-120p lướt/ngày/acc. Thời gian ngốn cả ca: 4.5 - 5.5 tiếng.
- Mới: 2 phiên x 30-35p = ~60-70p lướt/ngày/acc. Thời gian 1 ca chỉ còn ~1h45 - 2 tiếng.
- Giữa 2 phiên: Bắt buộc có khoảng nghỉ `pair_gap` ngẫu nhiên từ **35 đến 60 phút** (không chạy liên tù tì).

### B. Dời Hook Đăng Video Lên Phiên 2 (Phiên Cuối Ca)
- **Invariant:** Hook Đăng Video (`_run_upload_hook`) CHỈ được kích hoạt ở **Phiên cuối cùng của ca** (`session_index == 2`, thay vì `session_index == 3` như trước).
- Phiên 1: Lướt feed tương tác nhẹ, tạo warm telemetry.
- Phiên 2: Lướt feed + kích hoạt hook Đăng Video + Follow hook trước khi chốt ca.

### C. Điều Chỉnh Ngân Sách Follow (Follow Quota)
- Giữ nguyên trần an toàn: **35 follow/ngày**.
- Vì rút từ 3 phiên xuống 2 phiên, budget mỗi phiên phải tăng lên tương ứng:
  - Cũ (3 phiên): `budget_per_session_min: 9`, `budget_per_session_max: 12` (~10-12 follow/phiên).
  - Mới (2 phiên): `budget_per_session_min: 15`, `budget_per_session_max: 18` (~15-18 follow/phiên).
  - Nhịp follow: Trung bình ~2 phút mới bấm 1 follow trong suốt phiên 30-35 phút, đảm bảo tự nhiên và an toàn với thuật toán TikTok.

---

## 3. Cơ Chế Tản Nhiệt & Tắt Màn Hình Khi Máy Rảnh (Hardware Lifespan Invariant)

### A. Bối Cảnh & Vấn Đề
- Khi farm chạy 4 ca/ngày trên 80 máy Samsung, nếu giữ màn hình luôn sáng (`stay-awake` 24/7) thì máy sẽ nóng ran liên tục, gây phồng pin, ám màn AMOLED và crash uiautomator.

### B. Quy Chuẩn Tắt/Bật Màn Hình
1. **Tắt màn khi Idle (Giữa các phiên & giữa các ca):**
   - Trước khi tắt: Kiểm tra trạng thái màn hình qua `dumpsys display | grep mScreenState` (hoặc `mHoldingDisplaySuspendBlocker`).
   - CHỈ gửi lệnh `input keyevent 26` (Power) khi màn hình đang `ON`. CẤM bấm mù vì nếu màn hình đang tắt sẽ bị bật sáng ngược lại.
2. **Đánh thức trước phiên mới (Wake-up Gate):**
   - Trước khi preflight/mở app: Gửi `input keyevent 224` (Wakeup) + vuốt mở khóa (`input swipe 500 1500 500 500 200`).
   - Kiểm tra màn hình đã sáng và unlock thành công rồi mới khởi chạy app TikTok.
