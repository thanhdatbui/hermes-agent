# Khế Ước Follow Farm: Phân Biệt Ca/Phiên, Bản Chất Cooldown Streak & Thiết Kế A/B Test Max Volume (2026-10-28)

## 1. Chuẩn Hóa Thuật Ngữ & Chu Kỳ Vận Hành Farm
- **Cấu trúc Lịch chạy:**
  - 1 Ngày có **4 Ca lớn**: Ca 1 (Sáng: 06h–12h), Ca 2 (Chiều: 12h–18h), Ca 3 (Tối: 18h–24h), Ca 4 (Đêm: 00h–06h).
  - Mỗi Ca chia làm **2 Phiên** (Session): Phiên 1 (2 tiếng đầu ca) và Phiên 2 (4 tiếng sau của ca).
- **Chu kỳ quay vòng tài khoản (Rotation Cycle):**
  - Mỗi nick trên máy **3 ngày (72h) mới quay lại chạy 1 lần**.
  - Khi đến lượt, nick **chỉ chạy trong đúng 1 Ca (1 buổi gồm 2 phiên)** rồi nghỉ tiếp 3 ngày.
- **Phân biệt Trần Phiên vs Tổng Tăng Cả Ngày trên Dashboard:**
  - **Trần (Active Ceiling, 14–17 lượt):** Là trần khống chế cho **1 Phiên đơn lẻ (Session Burst Limit)** trong 5–10 phút mở app.
  - **Số biến động trên Dashboard (`+27`, `+22`):** Là **tổng cộng dồn cả 2 phiên trong ca** của ngày hôm đó (ví dụ Phiên 1: 14 + Phiên 2: 13 = 27 lượt). Hai khái niệm độc lập, không mâu thuẫn.

---

## 2. Bản Chất Kỹ Thuật: Cooldown, Streak & Bác Bỏ Ảo Giác "Nhả Ngược"
- **Quy tắc bất biến trong code (`follow_state.py`):**
  ```python
  if used > 0:
      streak = 1
  ```
- **Chạm trần ở đuôi (`used > 0`):**
  - Khi nick đã follow thành công $\ge 1$ người rồi mới bị TikTok nhả ở cuối phiên: Hệ thống **ép cứng `streak = 1`**, chỉ phạt cooldown nhẹ 24h để xả cache phiên.
  - Do chu kỳ quay vòng là 3 ngày (72h), án phạt 24h này đã tự động hết hạn từ lâu trước khi nick quay lại chạy cữ tiếp theo.
- **Chết Anchor đầu phiên (`used == 0`):**
  - Vừa bấm lượt 1 đã bị nhả ngay: Đây là dấu hiệu nick đang bị Action Block thật sự hoặc IP/proxy dính cờ đen. Lúc này hệ thống mới lũy tiến tăng `streak >= 2` (phạt nghỉ 3–15 ngày).
- **Bác bỏ ảo giác "Nhả ngược":**
  - Tuyệt đối KHÔNG có cơ chế TikTok âm thầm quét hủy các lượt follow đã bấm thành công trước đó trong cùng phiên. Số follow ăn được trước khi chạm trần là ăn thật 100%.

---

## 3. Thiết Kế A/B Test: Max Volume Bỏ Hồi Phục vs Bám Trần An Toàn

### Vấn đề của cơ chế cũ (Nút thắt cổ chai sản lượng)
Khi nick chạm trần ở đuôi (`used > 0`), dù `streak = 1` nhưng code lại kích hoạt `is_post_cooldown_warmup = True`, ép nick vào 2 ca "Dưỡng thương" (Hồi phục 1: 3–5 lượt, Hồi phục 2: 5–6 lượt). Với chu kỳ 3 ngày/lần, nick bị mất đứt **2 vòng chạy (6 ngày)** bị bóp sản lượng thê thảm dù bản thân nick rất trâu.

### Quy chuẩn A/B Split (Even / Odd Machines)
Chia theo **Số máy Chẵn / Lẻ** để cân bằng tải trên các cặp proxy 4G dùng chung:
- **Nhóm A — Máy Lẻ (M1, M3, M5... - Đối chứng):**
  - Giữ nguyên cơ chế hiện tại: Bám dải hẹp $[cap-2, cap]$, khi chạm trần thì bóp trần $lf - 2$ và trải qua Hồi phục 1 & 2.
- **Nhóm B — Máy Chẵn (M2, M4, M6... - Thử nghiệm Max Volume):**
  - **Cấp Quota Max:** Cấp thẳng **20 lượt / phiên** (1 buổi 2 phiên = max 40 lượt/ngày), không gò theo trần cũ.
  - **Chạm trần thì dừng:** Dính nhả ở lượt thứ $N \rightarrow$ ngắt phiên ngay, bỏ túi trọn vẹn $N-1$ lượt sạch.
  - **BỎ HỒI PHỤC 1 & 2:** Nếu `used > 0`, **CẤM giáng cấp về Hồi phục 1 & 2**. Vòng 3 ngày sau tới cữ vẫn cấp thẳng Full Quota (20 fl) tiếp.
  - **Chốt bảo hiểm:** Chỉ khi `used == 0` (chết anchor ngay phát đầu) mới cho Cooldown dưỡng thương.
- **Thời gian thử nghiệm:** Chạy liên tục **3 tuần (5–6 chu kỳ quay vòng)** để đủ mẫu kiểm chứng qua các đợt quét định kỳ của TikTok.

---

## 4. Hạ Tầng Proxy Dùng Chung & Cơ Chế Lệch Pha (Anti-Congestion)
- **Băng thông 4G MobiProxy:** Cổng 4G đạt 20–40 Mbps. Lướt Feed chỉ tốn 1.5–2.5 Mbps/máy, upload video 8–15 MB chỉ mất 5–10s.
- **Lệch pha tự nhiên:**
  - Hai máy chung proxy không cần khóa đợi nhau khi lướt Feed / Đăng Video vì pipeline đã cài sẵn `MachineStartStaggerMs` (lệch khởi động 2–8s) và `SessionJitter` (lệch nhịp 1–3 phút).
  - Riêng tiến trình **Follow** nhạy cảm thì chạy tuần tự lệch phút để chống kích hoạt bot-check trên cùng 1 IP.
