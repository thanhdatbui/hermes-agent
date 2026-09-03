# Chiến Lược Lịch Chẵn/Lẻ 2 Ca Follow/Ngày & Điều Chỉnh Budget Follow (19/08/2026)

## 1. Bối cảnh & Vấn đề Thực tế
- **Sáng 19/08/2026**: Row 1 chạy dồn 4-5 phiên liên tiếp trong buổi sáng (từ 06:00 đến 10:45), đạt 15-20 follow/nick. Đến phiên thứ 5 lúc 09:45, TikTok bắt đầu kích hoạt cơ chế nhả follow (`FOLLOW_FAILED`) hàng loạt trên 46/64 máy.
- **Thực nghiệm 21:45 tối 19/08**:
  - Máy sáng đã dính nhả (Máy 1): nghỉ 11 tiếng tối chạy lại VẪN BỊ NHẢ NGAY LƯỢT ĐẦU.
  - Máy sáng chưa chạm limit (Máy 10): tối chạy follow tiếp 4 người hoàn toàn bình thường.
  - **Kết luận quy luật**: Rate-limit của TikTok tính theo **ngày dương lịch (Calendar Day)**. Một khi đã dính cờ `follow_failed` trong ngày thì nghỉ 10-12 tiếng vẫn bị nhả, phải qua ngày hôm sau (`_roll_day`) mới phục hồi.
  - **Cơ chế chống spam của TikTok**: Quét tốc độ dồn dập (Burst velocity) nếu follow dồn trong 1 buổi. Do đó, bắt buộc phải **rải đều 2 cữ Sáng / Tối cách nhau 8-10 tiếng**.

---

## 2. Thiết Kế Lịch Chẵn / Lẻ (Chốt Cuối 19/08/2026)

### 🗓️ Cấu trúc Lịch 3 Ca / Ngày:
- **NGÀY LẺ (1, 3, 5, 7... trong tháng) — Lane B:**
  - **Ca 1 - Sáng (06:00 - 10:00, Jitter ±25p):** **Row 1** (3 phiên, mỗi phiên ăn 4-6 follow).
  - **Ca 2 - Trưa (12:30 - 16:30):** **Row 3** (Lướt Feed nuôi nick + Upload video lên ≥8 video, **0 follow**).
  - **Ca 3 - Tối (19:00 - 23:00, Jitter ±25p):** **Row 1** (3 phiên, mỗi phiên ăn 4-6 follow).
  - *Tổng kết Ngày Lẻ*: Row 1 ăn trọn **8-12 follow/ngày**, chia làm 2 cữ cách nhau 9 tiếng (an toàn tuyệt đối). Đăng 2 video/ngày.

- **NGÀY CHẴN (2, 4, 6, 8... trong tháng) — Lane A:**
  - **Ca 1 - Sáng (06:00 - 10:00, Jitter ±25p):** **Row 2** (3 phiên, mỗi phiên ăn 4-6 follow).
  - **Ca 2 - Trưa (12:30 - 16:30):** **Row 4** (Lướt Feed warm-up, **0 follow**).
  - **Ca 3 - Tối (19:00 - 23:00, Jitter ±25p):** **Row 2** (3 phiên, mỗi phiên ăn 4-6 follow).
  - *Tổng kết Ngày Chẵn*: Row 2 ăn trọn **8-12 follow/ngày**. Đăng 2 video/ngày.

- **Quy luật Nghỉ ngơi & Đăng Video:**
  - 1 ngày cày follow + đăng 2 video ➔ 1 ngày nghỉ hoàn toàn để ngấm tương tác và thuật toán phân phối.

---

## 3. Cập Nhật Kỹ Thuật Trong Mã Nguồn

### A. Hạ Budget Follow mỗi phiên (`follow_runner/config.example.yaml` - commit `395af9d`)
```yaml
budget_per_session_min: 4
budget_per_session_max: 6
budget_per_session: 6
```
- Tránh dồn quá 10 follow trong 1 phiên, giữ nhịp 4-6 follow/phiên.

### B. Cấu hình LANES Cron Scheduler (`hermes_cron/blocks.py` - commit `1f7225a`)
```python
# LANES cấu hình phân chia theo ngày Chẵn / Lẻ:
# Ngày Lẻ (Lane B): Ca 1 (Row 1) + Ca 2 (Row 3) + Ca 3 (Row 1 - Cữ 2)
# Ngày Chẵn (Lane A): Ca 1 (Row 2) + Ca 2 (Row 4) + Ca 3 (Row 2 - Cữ 2)
LANES = (("A", (2, 4, 2)), ("B", (1, 3, 1)))
```

### C. Jitter ngẫu nhiên liên tục từng phút (`hermes_cron/blocks.py` - commit `7053491`)
```python
# Thay vì tuple rời rạc (-20, -15, 15, 20), mở rộng dải số nguyên liên tục:
JITTER_MINUTES = tuple(range(-25, 26))
```
- Giúp 80 máy phân tán thời gian bật app ngẫu nhiên (-25 đến +25 phút), triệt tiêu hiện tượng khởi động đồng loạt (synchronized spike).

### D. Khóa Cứng Nick 0 Video (`multi_machine_feed_session.py` - commit `fba56f4`)
- Trong `_run_follow_hook`: kiểm tra `video_count <= 0` ➔ `status = "skipped"`, `reason = "zero-video-follow-disabled"`, bỏ qua hoàn toàn follow runner.

### E. Tự Động Phục Hồi Quyền Follow Khi Sang Ngày Mới (`follow_state.py` - commit `eaadbef`)
- Trong `_roll_day()`: khi `budget_date != today`:
  ```python
  if self._data.get("follow_failed_date") and self._data.get("follow_failed_date") != today:
      self._data["follow_failed"] = False
      self._data.pop("follow_failed_date", None)
  ```
  Nick tự động xóa cờ phạt và phục hồi quyền follow vào ngày mới mà không cần can thiệp thủ công.

---

## 4. Chiến Lược Vận Hành 2 Giai Đoạn
1. **Giai đoạn 1 (Hiện tại: ~200 nick)**:
   - Row 1 & Row 2 follow chéo toàn bộ danh sách ~200 nick hiện có đến khi cạn tệp (`exhausted`).
2. **Giai đoạn 2 (Mở rộng cho Row 3, 4, 5, 6)**:
   - Kích hoạt Render & Upload video cho Row 3, 4, 5, 6 để đạt $\ge 8$ video.
   - Khi các row mới có video ➔ Mở khóa follow ➔ Bể follow mở rộng lên 960 nick ➔ Đạt đích 1.000 Follower mở TikTok Shop.
