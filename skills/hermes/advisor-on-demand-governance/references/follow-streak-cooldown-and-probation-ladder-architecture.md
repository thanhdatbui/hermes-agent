# Kiến Trúc Chuỗi Phạt Nhả (Fail Streak) & Cấp Độ Quota Dưỡng Nick (Probation)

## 1. Nguyên Tắc Phân Tách 2 Hệ Thống Độc Lập
Tuyệt đối không được nhập nhằng giữa **Chuỗi thất bại (`fail_streak`)** và **Cấp độ Quota Dưỡng Nick (`probation_clean_days` / `graduated`)**:

| Tiêu chí | Chuỗi Phạt Nhả (`fail_streak`) | Cấp Độ Quota Dưỡng Nick (`probation`) |
| :--- | :--- | :--- |
| **Bản chất** | Đo lường xem nick có đang bị TikTok chặn cứng ở mức 0 hay không | Quản lý van tải lưu lượng (quota) để dưỡng nick không bị ngợp |
| **Khi follow được >= 1** | **Reset về 0 ngay lập tức** (chuỗi thất bại bị bẻ gãy) | Vẫn giữ nguyên nấc dưỡng (Hồi phục 1 hoặc 2) theo ngày sạch |
| **Điều khiển bởi** | `fail_streak`, `last_failed_date`, `cooldown_until_at` | `probation_clean_days`, `graduated`, `recovered_date` |

### Cạm bẫy thiết kế (Anti-Pattern đã khắc phục):
- **Lỗi cũ:** Bắt `fail_streak` phải giữ nguyên $> 0$ trong suốt thời gian dưỡng, chỉ khi nào "tốt nghiệp" (`graduated = True`) mới chịu về 0.
- **Hậu quả:** Nick vừa ra tù, chạy cữ đầu tiên cày được 3-4 follow sạch nhưng state vẫn bị ghim `fail_streak = 3`. Đến cữ sau lỡ nhả ở Anchor là bị script cộng dồn lên `Streak 4` (giam 15 ngày oan).
- **Quy chuẩn đúng:** Cứ bấm follow thành công dù chỉ 1 cái (`status == STATUS_FOLLOWED`) $\rightarrow$ `fail_streak = 0` ngay! Cấp độ dưỡng Quota vẫn chạy độc lập theo ngày sạch.

---

## 2. Thang Phạt Cooldown Khi Bị Nhả (Standardized Escalation Ladder)

| Mức Streak | Điều kiện kích hoạt | Thời hạn Cooldown | Ý nghĩa vận hành |
| :---: | :--- | :---: | :--- |
| **Streak 1** | - Bị nhả lần đầu tiên trong đời (`used == 0`)<br>- HOẶC chạm trần phiên sau khi đã follow được $\ge 1$ cái (`used >= 1`) | **24 giờ (1 ngày)** | Xả cache trong ngày. Tuyệt đối không giam 3 ngày. |
| **Streak 2** | Hết 24h chạy lại cữ đầu mà bị nhả tiếp 0 follow (tái phạm lần 2 liên tiếp) | **3 ngày** | Cách ly trung hạn (không phạt 5 ngày). |
| **Streak 3** | Hết 3 ngày chạy lại cữ đầu mà bị nhả tiếp 0 follow (tái phạm lần 3 liên tiếp) | **5 ngày** | Cách ly dài hạn (không phạt 7 ngày). |
| **Streak >= 4**| Tái phạm liên tiếp từ lần thứ 4 trở đi | **15 ngày** | Diện nghi vấn spammer nặng. |

---

## 3. Đồng Bộ Đa Repo Giữa `tiktok-follow` và `tiktok-luot nuoi acc`
- **Tại `follow_runner/core/follow_state.py`:**
  - `used > 0`: Gán `streak = 1`, cooldown `now_utc + 24 hours`.
  - `streak == 1`: cooldown 24h.
  - `streak == 2`: cooldown 3 days.
  - `streak == 3`: cooldown 5 days.
  - `streak >= 4`: cooldown 15 days.
  - Trong `mark(uid, STATUS_FOLLOWED)`: Hễ có follow thành công thì `self._data["fail_streak"] = 0` ngay.
- **Tại `python_runner/flows/multi_machine_feed_session.py` (`_is_account_follow_cooldown`):**
  - Bắt buộc tôn trọng `cooldown_until_at` / `cooldown_until_date` từ state, không tự ý hardcode đè công thức phạt cũ lên tài khoản.
  - Công thức streak days: `streak_days = 0 if streak == 0 else (1 if streak <= 1 else (3 if streak == 2 else (5 if streak == 3 else 15)))`.

---

## 4. Kỷ Luật Vận Hành Dispatch & Worker
- **`Worker floor 300s`:** CẤM Coordinator tự ý truyền cờ `--timeout` ngắn (như 30s) trong terminal làm ngắt ngang tiến trình streaming của worker.
- **Nguyên tắc Claude On-Demand:** 100% On-Demand, cấm tự ý gọi hoặc đề xuất chuyển giao cho Claude worker khi User không chỉ định đích danh.
