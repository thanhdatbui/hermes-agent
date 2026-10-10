# Dynamic Weak-Account Picker & Farm Rest Day Allocation (2026-10-11)

## 1. Bối Cảnh & Vấn Đề Cốt Tử Của Mô Hình "Batch Theo Row" Cũ

### Hiện trạng
Farm vận hành 160 máy Android (80 máy Kibe, 80 máy Admin), mỗi máy chứa 8 slot tài khoản TikTok (`Row 1` đến `Row 8`).
Trước đây, lịch chạy chia theo các ca cố định truyền tham số `-Row <N>`:
* Ví dụ: `run-feed-session.ps1 -Row 3` $\rightarrow$ Tất cả 80 máy đồng loạt mở Slot 3 lên chạy.

### Nghịch lý cào bằng (Resource Misallocation)
* **Máy 1:** Slot 3 đã rất khỏe (đã đăng 25 video, 500 follow, tương tác tốt) $\rightarrow$ vẫn bị lôi ra chạy tốn pin, mòn proxy.
* **Máy 12:** Slot 6 đang ngắc ngoải (mới 3 video, view đứng hình, bị nhả follow) $\rightarrow$ lại bị bỏ xó vì chưa đến phiên Row 6.
* **Global Batch Signature:** Việc 80 máy cùng mở app, cùng chọn slot 3, cùng thực hiện một luồng hành vi trong cùng khung giờ tạo ra footprint máy móc dễ bị thuật toán phát hiện.

---

## 2. Kiến Trúc "Dynamic Weak-Account Picker" (Chọn Slot Yếu Nhất Theo Từng Máy)

Thay vì bắt cả farm chạy chung một Row, hệ thống truy vấn cơ sở dữ liệu `D:/Taadaa/data/tiktok_tracker.db` để tính toán **Vulnerability Score (Điểm Sức Khỏe / Rủi Ro)** cho từng slot của từng máy.

### Công Thức Chấm Điểm Vulnerability Score (0 – 100)
$$\text{Score} = 100 \times (0.30 \times C + 0.40 \times P + 0.30 \times S)$$

1. **$C$ — Content Deficit (Thiếu hụt video, trọng số 30%):**
   $$C = \text{clamp}\left(\frac{10 - \text{video\_count}}{10}, 0, 1\right)$$
   * Nick có 0 video: $C = 1.0$ (ưu tiên cứu cao).
   * Nick $\ge 10$ video: $C = 0.0$ (đã đạt mốc an toàn).

2. **$P$ — Penalty / Restriction (Án phạt Cooldown, trọng số 40%):**
   * Đang dính án nhả follow (`follow_cooldown == True`): $P = 1.0$.
   * Vừa hết án cooldown trong 3 ngày: $P = 0.5$.
   * Tài khoản sạch: $P = 0.0$.

3. **$S$ — Stagnation (Đứng hình / Không tăng trưởng trong 7 ngày, trọng số 30%):**
   * $\Delta \text{View} = 0 \rightarrow$ Trọng số phễu cao nhất ($0.45$).
   * $\Delta \text{Heart} = 0 \rightarrow$ Trọng số tương tác ($0.30$).
   * $\Delta \text{Follower} = 0 \rightarrow$ Trọng số kết quả ($0.25$).
   $$S = 0.45 \times S_{\text{view}} + 0.30 \times S_{\text{heart}} + 0.25 \times S_{\text{follower}}$$

---

## 3. Quy Tắc Hành Động Bắt Buộc (Anti-Fraud Safety Invariant)

**CẢNH BÁO TỐI QUAN TRỌNG TỪ ADVISOR:**
> *"Tài khoản có điểm yếu cao KHÔNG ĐỒNG NGHĨA VỚI VIỆC ĐƯỢC ÉP CHẠY TƯƠNG TÁC NHIỀU HƠN!"*

Phân luồng hành động chuẩn theo từng nhóm trạng thái:
1. **Nhóm Cooldown ($P = 1.0$):**
   * **HÀNH ĐỘNG:** **HOLD / PURE FEED ONLY.**
   * CẤM BẤM FOLLOW (`_follow_rate = 0`). Chỉ cho lướt feed xả tải và đăng 1 video/ngày nếu chưa đủ 10 video.
2. **Nhóm Thiếu Video ($C > 0.5$, không cooldown):**
   * **HÀNH ĐỘNG:** Lướt feed warm nick + Upload video 1 video/ngày để mau chóng đạt mốc 10 video.
3. **Nhóm Khỏe Mạnh (Score < 20):**
   * Giữ nguyên lịch cày thông thường, không lôi vào ca dưỡng sinh làm hao mòn tài nguyên.

---

## 4. Phân Bổ Ca Chạy Chu Kỳ 4 Ngày Farm Chuẩn

| Khung giờ | Ngày 1 (Lẻ) | Ngày 2 (Chẵn) | Ngày 3 (7, 8 & Tối) | Ngày 4 (Nghỉ dưỡng sinh toàn farm) |
| :--- | :---: | :---: | :---: | :---: |
| **Ca 1 (06h & 08h)** | **Row 1** (Cày) | **Row 2** (Cày) | **Row 7** (Cày) | **Row 3** (Dưỡng sinh pure feed + Up) |
| **Ca 2 (12h & 14h)** | **Row 3** (Cày) | **Row 4** (Cày) | **Row 8** (Cày) | **Row 4** (Dưỡng sinh pure feed + Up) |
| **Ca 3 (18h & 20h)** | **Row 5** (Cày) | **Row 6** (Cày) | **Row 3 / 4** (Dưỡng sinh) | **Row 5 / 6** (Dưỡng sinh pure feed + Up) |

* **Ngày 5:** Gieo xúc xắc random 50/50 giữa Ngày 1 và Ngày 2 để bắt đầu chu kỳ 4 ngày mới, phá footprint định kỳ của hệ thống.
* **Nguyên tắc Upload Video:** Mọi ca dưỡng sinh và nick dính Follow Cooldown **VẪN ĐƯỢC PHÉP ĐĂNG 1 VIDEO/NGÀY** (mở Upload Hook cả Phiên 1 & Phiên 2, khóa bằng sổ cái `shift_upload_history.json`).
