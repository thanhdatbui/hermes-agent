# Cron Safe Source Sync & Row 5-6 Warmup Schedule

## 1. Single Source of Truth Invariant: `taikhoan_run_safe.xlsx`
- **Nguyên tắc bất biến:** `taikhoan_run_safe.xlsx` (480 rows = 80 máy x 6 slots) là nguồn sự thật duy nhất cho toàn bộ hệ thống Cron điều phối nuôi nick TikTok.
- **CẤM:** Tự ý tạo workbook trung gian, chia tách file hoặc hardcode dải máy (ví dụ chỉ chạy 1..74 máy).
- **Tự động đồng bộ 3 tầng (`hermes_taikhoan_sync_cron.py`):**
  1. Đọc trực tiếp `taikhoan_run_safe.xlsx`.
  2. Lọc bỏ các ID rác (`ghjfghj`, `none`, `null`), nạp trọn bộ đủ 80 máy (1..80) và sinh `hermes_cron_source_config.json`, `feed_state.json`, `post_state.json`.
  3. **Tái tạo Manifest tức thời:** Khi `source_revision` thay đổi, tự động dọn manifest cũ trong ngày và kích hoạt `tiktok_picker.py` tái tạo manifest mới đồng bộ, ngăn ngừa tuyệt đối lỗi `MANIFEST_IDENTITY_MISMATCH` trên `phase9-watcher-tiktok-feed`.

---

## 2. Farm Schedule Matrix & Phân bổ ca nuôi mới
- **Quy tắc phân chia ca nuôi theo Parity:**
  + **Ngày Lẻ (Lane B):** Ca 1 (06:00 - Row 1) + Ca 2 (12:30 - Row 3) + Ca 3 (19:00 - Row 5).
  + **Ngày Chẵn (Lane A):** Ca 1 (06:00 - Row 2) + Ca 2 (12:30 - Row 4) + Ca 3 (19:00 - Row 6).
- **Phân bổ mục tiêu từng Row:**
  + **Row 1 & Row 2 (Đã nuôi cứng):** Chỉ nuôi ca Sáng (Ca 1). Phiên 3 đăng video + Follow chéo (Gate $\ge 5$ video).
  + **Row 3 & Row 4:** Nuôi ca Chiều (Ca 2). Lướt feed + Đăng video.
  + **Row 5 & Row 6 (Nick mới):** Nuôi ca Tối (Ca 3). Warmup an toàn theo lộ trình.

---

## 3. Lộ trình Warmup Chuẩn cho Nick Mới (Row 5 & 6)
Do chạy xen kẽ 2 ngày 1 lần (ngày Chẵn/Lẻ), lộ trình tính theo ngày lịch như sau:
1. **Giai đoạn 1 (Ngày 1 $\rightarrow$ 10 lịch = 5 ngày chạy thực tế):**
   - Chỉ lướt Feed thuần (15 phiên lướt).
   - **0 video, 0 follow.** Tạo cookie tự nhiên và định hình trust score.
2. **Giai đoạn 2 (Ngày 11 $\rightarrow$ 20 lịch = 5 ngày chạy thực tế tiếp theo):**
   - Lướt feed + mỗi ngày đăng 1 video ở Phiên 3.
   - Vẫn khóa follow (`under-5-videos-follow-disabled`).
3. **Giai đoạn 3 (Từ ngày 21 lịch trở đi):**
   - Đã đạt đủ mốc $\ge 5$ video/nick.
   - Hệ thống tự động mở Gate Follow chéo ngoài farm (Module 2).
