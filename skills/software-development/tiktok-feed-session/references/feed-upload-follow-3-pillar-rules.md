# Quy Tắc Điều Phối 3 Trụ Cột: Feed + Upload + Follow (Lịch 4 Ca x 2 Phiên)

*Được cập nhật và chuẩn hóa ngày 12/09/2026 sau Case 150, 151, 152.*

---

## 1. Kiến Trúc 4 Ca x 2 Phiên (HCMC Timezone)
- **Ca 4 (Đêm):** `00:00` (Phiên 1) & `01:30` (Phiên 2) — Ngày chẵn Row 8 / Ngày lẻ Row 7.
- **Ca 1 (Sáng):** `06:00` (Phiên 1) & `08:00` (Phiên 2) — Ngày chẵn Row 2 / Ngày lẻ Row 1.
- **Ca 2 (Trưa):** `12:00` (Phiên 1) & `14:00` (Phiên 2) — Ngày chẵn Row 4 / Ngày lẻ Row 3.
- **Ca 3 (Tối):** `18:00` (Phiên 1) & `20:00` (Phiên 2) — Ngày chẵn Row 6 / Ngày lẻ Row 5.
- **Dead Zone:** `02:30` đến `05:59` (Nghỉ máy hoàn toàn, chỉ chạy job background/backup nếu có).

---

## 2. Quy Tắc Upload Hook (Case 150 & Case 152)
- **Mục tiêu:** Đăng tối đa 1 video / ca cho mỗi máy/tài khoản, nhưng linh hoạt ở **CẢ PHIÊN 1 VÀ PHIÊN 2**.
- **Cơ chế chống đăng trùng:** Bắt buộc dùng `_ShiftUploadLedger` (atomic file lock `history.json`).
  - **Phiên 1:** Sau khi lướt feed, kiểm tra có video theo Row trong workbook Tik $\rightarrow$ Đăng ngay.
  - **Phiên 2:** Kiểm tra ledger:
    - Nếu Phiên 1 **đã đăng thành công** $\rightarrow$ Safe-Skip ngay trong 0.1s (`reason: already_uploaded_in_shift`).
    - Nếu Phiên 1 **chưa đăng / đăng lỗi** (mạng rớt, proxy đóng, v.v.) $\rightarrow$ Tự động đăng bù ở Phiên 2.
- **Cờ kích hoạt CLI:**
  - `run_tiktok.py`: `--allow-upload-hook` và `--session-index {1,2}`.
  - `run-feed-session.ps1`: Luôn truyền `--allow-upload-hook` khi chạy local/scheduled run.

---

## 3. Quy Tắc Follow Hook (Case 151)
- **Gate kiểm tra duy nhất:** Bắt buộc nick có **tối thiểu 5 video (`video_count >= 5`)** mới được phép kích hoạt follow chéo.
- **Tuyệt đối không chặn cứng theo Row:**
  - CẤM các logic gán cứng kiểu `if row in (3, 4, 5, 6): return skipped "warmup"`.
  - Mọi Row (Row 1..8), bất kỳ nick nào có `video_count >= 5` đều được đi follow sau khi lướt feed.
  - Nick có `video_count < 5` tự động Safe-Skip với lý do `under-5-videos-follow-disabled` để bảo vệ nick khỏi bị nhả follow do trust thấp.

---

## 4. Kỷ Luật Báo Cáo Chốt Phiên & Watchdog
- **Báo cáo bắt buộc 3 trụ cột:** Mọi báo cáo ca nuôi acc / đóng phiên BẮT BUỘC liệt kê đủ 3 phần:
  1. **Lướt Feed:** Success / Failed / Proxy-VPN blocked / Manual-needed.
  2. **Upload Video:** Đã đăng / Safe-skip (đã đăng P1 / hết video) / Lỗi.
  3. **Follow Hook:** Lượt follow thành công / Safe-skip (<5 video / cooldown) / Lỗi.
- **Tránh nhầm lẫn im lặng:** Không bao giờ được bỏ qua cột Follow chỉ vì phiên đó không có nick nào đủ điều kiện follow — phải giải thích rõ lý do skip (ví dụ: "77 máy skip do < 5 video").
