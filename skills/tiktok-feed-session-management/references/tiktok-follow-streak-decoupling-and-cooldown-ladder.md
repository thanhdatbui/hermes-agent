# TikTok Follow: Bóc Tách Fail Streak vs Quota Tier & Chuẩn Hóa Cooldown Ladder

## 1. Bản Chất 2 Hệ Thống Độc Lập 100%
Trước đây hệ thống bị lỗi nghiêm trọng do nhập nhằng giữa **Bộ đếm chuỗi thất bại (`fail_streak`)** và **Tầng Quota Dưỡng Nick (`probation / graduation`)**, khiến nick vừa mãn hạn ra cày được follow sạch nhưng vẫn bị ghim streak cũ, cữ sau lỡ nhả là bị kích hoạt tái phạm oan lên Streak 3, 4 (giam 7–15 ngày).

### A. Hệ thống 1: `fail_streak` (Chuỗi thất bại liên tiếp)
- **Quy tắc vàng:** Trong `mark(uid, STATUS_FOLLOWED)`, **cứ follow thành công dù chỉ 1 người (`used >= 1`) $\rightarrow$ `self._data["fail_streak"] = 0` ngay lập tức!**
- Chuỗi thất bại bị bẻ gãy ngay tại thời điểm có follow thành công. Không bao giờ để nick đang follow được phải mang án streak 1, 2, 3.
- **Thang phạt Cooldown chuẩn hóa khi dính nhả:**
  - **Chạm trần phiên (`used > 0`):** Đã cày được $\ge 1$ người rồi mới đứt $\rightarrow$ Coi là chạm trần phiên của nick bình thường, tính là **`Streak 1` (nhả lần đầu), cooldown đúng 24 giờ**.
  - **Nhả cữ đầu (`used == 0`):** Vừa vào bấm bị từ chối ngay phát đầu tiên:
    - **`Streak 1`:** Cooldown **24 giờ** (1 ngày).
    - **`Streak 2`:** Cooldown **3 ngày** (+3 ngày đến 23:59:59 local).
    - **`Streak 3`:** Cooldown **5 ngày** (+5 ngày đến 23:59:59 local).
    - **`Streak >= 4`:** Cooldown **15 ngày** (diện tái phạm nặng).

### B. Hệ thống 2: Cấp độ Quota Dưỡng Nick (Hồi phục 1 ➔ Hồi phục 2 ➔ Khỏe)
- Chạy **độc lập 100%** qua `probation_clean_days` và `graduated`, tuyệt đối không phụ thuộc vào `fail_streak`:
  - **Hồi phục 1:** Cấp quota 2–4 lượt.
  - **Hồi phục 2:** Cấp quota 4–6 lượt.
  - **Khỏe (Tốt nghiệp / Graduated):** Cấp quota full 10–15 lượt.
- Khi nick hết cooldown ra chạy lại: Nick bắt đầu ở tầng Hồi phục 1 với `fail_streak = 0`. Dù `fail_streak` đã về 0, cờ `probation_clean_days` và `recovered_date` vẫn giữ nick chạy nhẹ 2–4 lượt, không bị vọt lên full quota. Nếu cữ sau có lỡ bị nhả thì nick chỉ bị phạt lại ở mức Streak 1 (24h), không bao giờ bị đè lên Streak 2, 3, 4 giam oan.

## 2. Kỷ Luật Vận Hành Runner & Tầng Điều Phối Worker
- **Đồng bộ Runner nuôi Feed (`multi_machine_feed_session.py`):**
  - Hàm `_is_account_follow_cooldown` bắt buộc tôn trọng `cooldown_until_at` và `cooldown_until_date` từ `follow_state`.
  - Không được hardcode công thức phạt 3/5/7 ngày đè lên state. Khi nick có `streak <= 1`, cooldown chỉ tính đúng 1 ngày.
- **Kỷ luật Worker Floor 300s & Anti-Reflexive Claude:**
  - CẤM Coordinator tự ý truyền flag `--timeout < 300` (như `--timeout 30`) trong terminal call cho dispatch worker. Sàn tối thiểu là 300s để worker stream không bị timeout.
  - Claude Worker / Advisor là **100% On-Demand**. CẤM Coordinator có phản xạ tự gọi, hội chẩn hay đưa Claude Worker ra khi User không yêu cầu đích danh. Tầng cơ học `sol_worker.py` / `dispatch_worker.py` đã chuẩn hóa, cấm Coordinator tự ý sửa phá.
