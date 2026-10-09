# Eight-Slot Incubator & Night Chain Feed Fallback Architecture

## Bối Cảnh & Mục Tiêu
Hệ thống Taadaa Phone Farm ban đầu vận hành theo chuẩn 6 accounts/máy (80 máy x 6 = 480 accounts) cho 3 ca ban ngày (Tik1..Tik6).
Khi mở rộng reg lên tối đa 8 accounts/máy (Slot 7 và Slot 8):
- Slot 7 và 8 đóng vai trò là **"Vườn ươm" (Incubator Slots)**: Chỉ phục vụ nuôi đệm lướt feed tích trust score (48–72h), tuyệt đối **CẤM** đưa vào pipeline đăng video để tránh làm lệch kho video render (`D:\TIKTOK-videonuoinick`) và đứt chuỗi kênh.
- Các tài khoản cứng cáp ở Slot 7/8 sau khi ươm sẽ được logout an toàn và luân chuyển sang Farm Admin (giải quyết bài toán farm Admin thiếu proxy để reg mới).

---

## 1. Cơ Chế Chuyển Nhánh Ca Đêm (Night Chain Dynamic Fallback)

Trong script điều phối ca đêm `D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py` (chạy 01:00 AM hàng ngày):

```text
[01:00 AM: Bắt đầu Chuỗi Đêm]
       │
       ▼
[Phase 1: Reg Gmail (run_all.ps1)]
       │
       ▼
[Phase 2: Reg TikTok (_run_all_targets.py)]
       ├──> CÒN TARGET REG (> 0 máy):
       │      ├─> Thực hiện đăng ký TikTok bình thường.
       │      └─> Chuyển sang Phase 3: Add 2FA TikTok.
       │
       └──> HẾT TARGET (Total targets: 0 / Full 8 acc toàn farm):
              │
              ├─> Kích hoạt Fallback: Ca Nuôi Feed Row 7 hoặc Row 8 theo ngày chẵn/lẻ.
              └─> Phase 3 (Add 2FA) VẪN TIẾP TỤC CHẠY BÌNH THƯỜNG SAU ĐÓ (quét bù 2FA cho các nick tồn/deferred).
```

### Các Quy Tắc Kỹ Thuật Đã Audit (Cập nhật 2026-09-07):
1. **Single Source of Truth cho Detection (Chống Double-Run):**
   - CẤM chạy preflight `_detect_clean.py` riêng rẽ trước Phase 2 rồi mới gọi `_run_all_targets.py`.
   - Cho Phase 2 thực thi `_run_all_targets.py`. Nếu toàn farm đã đủ 8 nick hoặc hết mail nguồn, script trả về `Total targets: 0` trong vòng 2-3 giây. Parser bắt chuỗi `Total targets: 0` để lập tức kích hoạt fallback nuôi feed ngay tại chỗ.
2. **Xác Định Row Nuôi Theo Ngày Chẵn / Lẻ (Tránh Bẫy Timezone):**
   - BẮT BUỘC dùng timezone `ZoneInfo("Asia/Ho_Chi_Minh")` tường minh:
     ```python
     from zoneinfo import ZoneInfo
     now_hcm = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
     # Ngày chẵn chạy Row 8, Ngày lẻ chạy Row 7
     feed_row = 8 if (now_hcm.day % 2 == 0) else 7
     ```
   - CẤM dùng `datetime.now()` trần vì nếu máy chủ hoặc môi trường container chạy theo giờ UTC (18:00 hôm trước), ngày sẽ bị lệch 1 ngày làm đảo lộn chu kỳ nuôi.
3. **Phase 3 (Add 2FA) Vẫn Tiếp Tục Chạy Sau Fallback (User Rule 2026-09-07):**
   - Kể cả khi Phase 2 chuyển sang nuôi feed fallback (do 0 target reg mới), **Phase 3 (Add 2FA) VẪN BẮT BUỘC CHẠY BÌNH THƯỜNG** sau khi nuôi feed xong.
   - Lý do: Phase 3 rà soát toàn bộ workbook để add 2FA bù cho các tài khoản đăng ký ở các ca trước, tài khoản deferred hoặc nick tồn chưa kịp bật 2FA. Tuyệt đối KHÔNG bỏ qua Phase 3.
4. **Quy Chuẩn Gọi Fallback Trong Pipeline (`run_night_chain_pipeline.py`):**
   - Hàm `run_tiktok_feed_fallback_batch(row: int) -> tuple[int, str]`:
     Gọi `run-feed-session.ps1` với `-Row $row -Preset full -LocalRun -RecoveryTestSwipes 2 -MaxWorkers 40 -Run`.
   - Timeout 3600s: Bọc try/except an toàn, khi dính `TimeoutExpired` hoặc ngoại lệ, bắt buộc dọn dẹp tiến trình con bằng `taskkill /T /F /PID <pid>`.
   - Format báo cáo Telegram chuẩn:
     `Phase 2 (Nuôi Feed Row {feed_row} [{'Ngày chẵn' if feed_row == 8 else 'Ngày lẻ'}] - Code {code}):`

---

## 2. Nâng Cấp Workbook & Bảo Toàn Tuyệt Đối Ca Ban Ngày (Row 1..6)

1. **Autoritative Generator duy nhất (`sync-safe-workbook.py`):**
   - Cron 5 phút (`hermes_taikhoan_sync_cron.py`) gọi trực tiếp `scripts/sync-safe-workbook.py`.
   - Khi nâng cấp `sync-safe-workbook.py` từ 6 lên 8 dòng/máy:
     * `while len(entries) < 8:`
     * `for i, (serial, account_id) in enumerate(entries[:8]):`
     * Với `EXTRA_MACHINES`: `for _ in range(8):`
2. **Byte-Identical Cho Row 1..6 (Chống Lệch Ca Ngày):**
   - Cấu trúc `taikhoan_run_safe.xlsx` duy trì thứ tự cố định theo STT máy.
   - 6 slot đầu tiên của mỗi máy giữ nguyên 100% thứ tự gán nick như cũ. Slot 7 và 8 chỉ được append vào cuối danh sách của từng máy.
3. **Cơ Chế Bỏ Qua An Toàn Cho Máy Chưa Đủ 8 Acc:**
   - Trong `python_runner/core/feed_session_workbook.py`, dòng 353-355:
     ```python
     elif not account.expected_username:
         reason = f"account row {row_index} is empty (no username) for machine {machine}, skipping"
     ```
   - Máy nào chỉ mới có 6 hoặc 7 acc, khi chạy ca Row 8 (hoặc Row 7) thì `account_id` rỗng $\rightarrow$ runner tự động skip an toàn, không văng exception, không chọn nhầm nick của slot khác.

---

## 3. Khóa Cứng Lớp Video (Hard Gate - Chống Đăng Nhầm Acc Nuôi Đêm)

1. **Cột 'Video Đã Đăng' Trong `taikhoan_run_safe.xlsx`:**
   - Acc ở Slot 7 và 8 không có file mapping con (`Tik7.xlsx` hay `Tik8.xlsx` không tồn tại).
   - Khi sync, `video_counts.get(account_id, 0)` mặc định bằng 0.
2. **Không Cấp Thư Mục Render (`Folder Video`):**
   - Không render video cho các slot > 6 (`D:\TIKTOK-videonuoinick`).
   - Runner upload có cơ chế Fail-Safe: Không có folder hoặc folder rỗng sẽ tự động skip `SKIP_NO_VIDEO_DIR`, tuyệt đối không đăng nhầm video của nick khác.
