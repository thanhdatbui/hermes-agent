# Farm Cron Schedule Architecture: Stagger, Alternating Cohorts & Persona Cadence

## 1. Physical Farm Reality (Anti-Hallucination)

- **Quy mô:** Farm vận hành **160 máy song song độc lập** (không chạy tuần tự 1 máy làm hết 160 máy).
- **Phân bổ tài khoản:** Mỗi máy Galaxy S7 chứa tối đa 8 tài khoản TikTok (Row 1 đến Row 8).
- **Lịch chạy luân phiên Ngày Chẵn / Ngày Lẻ (Alternating Days):**
  - **Ngày Lẻ:** Chỉ chạy 4 nick lẻ: Row 1 (Ca 1), Row 3 (Ca 2), Row 5 (Ca 3), Row 7 (Ca 4). 4 nick chẵn nghỉ 100%.
  - **Ngày Chẵn:** Chỉ chạy 4 nick chẵn: Row 2 (Ca 1), Row 4 (Ca 2), Row 6 (Ca 3), Row 8 (Ca 4). 4 nick lẻ nghỉ 100%.
  - **Mỗi nick nghỉ liên tục 32–36 tiếng** giữa 2 chu kỳ hoạt động.

---

## 2. Shift Cadence & Screen-On Budget

Mỗi ngày chia làm **4 Ca**:
- **Ca 1 (Sáng):** 06:00 (Phiên 1: Feed) & 08:00 (Phiên 2: Upload).
- **Ca 2 (Trưa):** 12:00 (Phiên 1: Feed) & 14:00 (Phiên 2: Upload).
- **Ca 3 (Tối):** 18:00 (Phiên 1: Feed) & 20:00 (Phiên 2: Upload).
- **Ca 4 (Đêm):** 00:00 (Phiên 1: Feed) & 01:30 (Phiên 2: Upload).

### Tải thực tế trên máy S7:
- Mỗi máy chạy **4 nick × 2 phiên = 8 phiên / ngày**.
- Mỗi phiên kéo dài **7 – 8 phút**.
- **Tổng thời gian sáng màn hình (Screen-on Time):** ~64 phút / 24 giờ (< 1.1 tiếng/ngày).
- Máy nghỉ ngủ sâu (deep sleep/idle) hơn 22 tiếng/ngày $\rightarrow$ Hoàn toàn an toàn cho pin và phần cứng S7.

---

## 3. Phân biệt Macro Persona Schedule vs Micro Jitter

### A. Macro Persona Schedule (BẮT BUỘC CỐ ĐỊNH):
- Khung giờ và ngày của từng nick phải **cố định 100%**: Row 1 luôn thức Ca Sáng ngày lẻ, Row 7 luôn thức Ca Đêm ngày lẻ.
- Mục đích: Xây dựng nhịp sinh học người dùng nhất quán (persona consistency) trong mắt thuật toán TikTok. Không được xáo trộn kiểu hôm nay chạy sáng mai chạy đêm.

### B. Micro Jitter (NGẪU NHIÊN HÓA ĐỘ TRỄ):
1. **Cron Trigger:** Cron đánh thức mỗi 15 phút (`*/15 * * * *`).
2. **Session Start Jitter (`run-feed-session.ps1` dòng 421–430):**
   ```powershell
   $SessionJitterMinSeconds = 60
   $SessionJitterMaxSeconds = 180
   $sessionJitterSec = Get-Random -Minimum 60 -Maximum 181
   Start-Sleep -Seconds $sessionJitterSec
   ```
   PowerShell tự động ngủ ngẫu nhiên **1 đến 3 phút (60s–180s)** trước khi kích hoạt máy.
3. **Machine Order & Stagger (`multi_machine_feed_session.py`):**
   - `-RandomizeMachineOrder`: Xáo trộn ngẫu nhiên thứ tự máy mỗi lần chạy.
   - `-MachineStartStaggerMs "2000,8000"`: Khởi động lệch nhau 2s đến 8s giữa các máy.

---

## 4. Invariant: CẤM TĂNG JITTER LÊN 3–5 PHÚT

- **Lý do an toàn:** Khoảng cách giữa Ca 4 Phiên 1 (00:00) và Phiên 2 (01:30) chỉ có 90 phút.
- Nếu tăng jitter lên 5 phút + thời gian chạy 35 phút $\rightarrow$ các máy cuối sẽ chạm sát giờ bắt đầu Phiên 2, kích hoạt cảnh báo giả (false alarm) của `feed_session_watchdog` (như sự cố 22 máy đỏ ca đêm trước đây).
- **Kết luận:** Giữ nguyên Session Jitter ở mức chuẩn **60s – 180s (1–3 phút)**.
