# Cron Fleet Lane Parity, Source Config Sync & Row 5-6 Warmup Protocol

## 1. Cấu hình phân chia Ca & Phân bổ Ngày Chẵn / Lẻ (Lanes)
Lịch nuôi farm phân bổ theo chu kỳ cách nhật (Parity Lanes) trong `python_runner/hermes_cron/blocks.py`:
- **Ngày Lẻ (Lane B):**
  + Ca 1 (06:00): **Row 1** (Feed + Đăng video ở Phiên 3 + Follow chéo).
  + Ca 2 (12:30): **Row 3** (Feed + Đăng video ở Phiên 3).
  + Ca 3 (19:00): **Row 5** (Warmup lướt Feed thuần).
- **Ngày Chẵn (Lane A):**
  + Ca 1 (06:00): **Row 2** (Feed + Đăng video ở Phiên 3 + Follow chéo).
  + Ca 2 (12:30): **Row 4** (Feed + Đăng video ở Phiên 3).
  + Ca 3 (19:00): **Row 6** (Warmup lướt Feed thuần).

```python
LANES = (("A", (2, 4, 6)), ("B", (1, 3, 5)))
```

---

## 2. Lộ trình Warmup An toàn cho Tài khoản Mới (Row 5 & 6)
Do chạy cách nhật (2 ngày chạy 1 lần), lộ trình chuẩn 20 ngày trước khi mở follow:
1. **Giai đoạn 1 (Ngày 1 - 10 lịch = 5 ngày chạy thực tế):**
   - 3 phiên/ngày = 15 phiên lướt feed thuần.
   - **CẤM đăng video, CẤM follow.**
2. **Giai đoạn 2 (Ngày 11 - 20 lịch = 5 ngày chạy thực tế tiếp theo):**
   - Bắt đầu đăng 1 video/ngày ở Phiên 3 $\rightarrow$ đạt mốc 5 video.
   - **VẪN CẤM follow.**
3. **Giai đoạn 3 (Từ Ngày 21 lịch trở đi):**
   - Nick đã đạt $\ge 5$ video và có trust score an toàn $\rightarrow$ Hệ thống tự động mở Gate follow chéo.

---

## 3. Quy tắc Đồng bộ Source Config & Tự động Re-arm Manifest
- **Nguồn sự thật duy nhất:** `taikhoan_run_safe.xlsx` (chứa đầy đủ 80 máy x 6 rows = 480 rows).
- **Cơ chế sync tự động trong `hermes_taikhoan_sync_cron.py`:**
  1. Đồng bộ 1-chiều ID từ `taikhoan_dat_v2` sang `Tik1..Tik6.xlsx` (bỏ blacklist chuỗi nhầm `vo.my`, `ngomai.ly`).
  2. Đồng bộ sang `taikhoan_run_safe.xlsx`.
  3. Trực tiếp trích xuất toàn bộ 80 máy sang `cron-source/hermes_cron_source_config.json`, `feed_state.json`, `post_state.json`.
  4. **Tự động xóa manifest/bundle cũ trong ngày và gọi `tiktok_picker.py` tái tạo manifest mới** để `source_revision` luôn khớp 100%, triệt tiêu hoàn toàn lỗi `MANIFEST_IDENTITY_MISMATCH` trên `tiktok_watcher` / `tiktok_runner`.

---

## 4. Gating Báo Cáo Watchdog (`can_report_session`)
- Watchdog chốt báo cáo phiên phải luôn kiểm tra `is_feed_runner_active()`.
- **Nguyên tắc fail-closed:** Nếu runner vẫn đang có tiến trình chạy (`runner_busy=True`), watchdog BẮT BUỘC trả về `False` (không được phát báo cáo giữa chừng khi vừa chạm mốc `window_end_hm` làm thiếu hụt số lượng máy thực tế).
