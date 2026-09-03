# Upload Hook Shift Dedup & Output Verification Rules

## 1. Quy tắc cốt lõi: 1 Video / Ca / Ngày ở Phiên 3
- Farm TikTok vận hành theo nguyên tắc: Mỗi ca có 3 phiên (Phiên 1 lướt, Phiên 2 lướt, Phiên 3 lướt + upload video).
- **Tuyệt đối không được phép upload quá 1 video / ca / ngày trên cùng 1 máy / acc.**
- Nếu một phiên 3 bị lỗi hoặc bị watchdog re-trigger, cơ chế phòng vệ phải đảm bảo các máy đã upload thành công không bị upload thêm lần 2, lần 3 (`video N+1`, `video N+2`).

## 2. Atomic Shift Dedup Ledger (`_ShiftUploadLedger`)
Trước khi gọi subprocess `tiktok_workflow`, runner bắt buộc thực hiện kiểm tra và khóa nguyên tử thông qua `_ShiftUploadLedger`:
1. **Khóa liên tiến trình (`_InterProcessFileLock`)**: Sử dụng file lock hệ điều hành (`msvcrt.locking` trên Windows, `fcntl.flock` trên POSIX) bao quanh file state `shift_upload_history.json` để ngăn chặn triệt để Race Condition giữa các worker chạy song song.
   - *Pitfall Lock Contention*: Khi 50+ máy đồng loạt hoàn tất lướt feed và bước vào upload, tất cả cùng tranh chấp file lock này. Nếu lock timeout đặt quá ngắn (như mặc định 10s) và bên trong lock thực hiện quét đĩa (`report_root.glob(...)`), các máy xếp hàng sau sẽ bị quá hạn `TimeoutError` dẫn đến lỗi `shift_upload_lock_timeout_fail_closed` (hiển thị thành `Timeout/Quá giờ` trên watchdog). Timeout của ledger lock phải đủ rộng và tránh I/O nặng bên trong critical section.
2. **Tương thích đa khóa (Dual-Key / Migration Schema)**: Đối soát đồng thời theo:
   - Canonical key: `{logical_day}_m{machine}_{acc_tag}`
   - Legacy / Shift key: `{logical_day}_shift_{row}_m{machine}_{acc_tag}`
   - Compact key: `{logical_day}_m{machine}_row{row}`
   Đảm bảo an toàn 100% ngay cả khi hoán đổi thứ tự row trong workbook hoặc rolling deploy.
3. **Kiểm tra State & Ground Truth**:
   - Nếu bất kỳ candidate key nào có trạng thái `success`, `launched`, hoặc `indeterminate`, runner **bắt buộc Safe-Skip ngay lập tức** (`status: skipped`, `reason: already_uploaded_in_shift`).
   - Quét Ground Truth reports trong `D:\CodexRuntime\tiktok-video\runs\run_{serial}_{date_compact}_*/report.json`. Nếu đã tồn tại report `status == SUCCESS` và `post_verified == True`, tự động cập nhật ledger và Safe-Skip.
4. **Vòng đời nguyên tử (Atomic Lifecycle Management)**:
   - `claim_reservation`: Đặt chỗ trạng thái `in_progress` kèm token UUID duy nhất và TTL an toàn (7200s).
   - `record_launched`: Chuyển trạng thái sang `launched` ngay **trước khi** spawn subprocess. Nếu ghi thất bại, abort ngay lập tức không spawn.
   - `complete_success`: Khi subprocess và verification hoàn tất thành công, thăng cấp trạng thái thành `success` bền vững.
   - `record_spawn_failed`: Nếu `Popen` thất bại ở cấp hệ điều hành (lỗi binary/CWD chưa spawn), tự động rollback reservation để cho phép retry.
   - `release_reservation`: Chỉ giải phóng an toàn khi subprocess **chưa từng được spawn** (queue timeout / preflight deadline). Khi subprocess đã spawn, trạng thái `launched` trên đĩa được giữ nguyên vẹn để chặn upload lặp.

## 3. Subprocess Execution & Output Verification Matching
- **Khởi chạy tiến trình an toàn**: Tách biệt bước khởi tạo `subprocess.Popen` và giao tiếp `proc.communicate(timeout=...)` để tránh nhận diện sai lỗi spawn khi có exception I/O / decode sau khi process đã chạy.
- **Nhận diện log worker chuẩn**:
  - `Workflow completed successfully`
  - `Report saved: <path>` (hỗ trợ trích xuất đường dẫn có khoảng trắng / dấu ngoặc kép)
  - `post verification passed` / `upload video success` / `upload completed`
- **Định vị & Kiểm chứng Report Ground Truth**:
  - Trích xuất `run_id` hỗ trợ cả dấu chấm (`[a-zA-Z0-9_\-\.]+`).
  - Resolve đường dẫn report đối soát theo cả `tiktok_video_runtime_root` và `tiktok_repo`.
  - Kiểm chứng toàn diện `report.json` trên đĩa: `status == SUCCESS`, `post_verified is True`, khớp `video_number == next_video`, khớp `device_id` và `account`.
  - **Report VETO**: Nếu file report tồn tại trên đĩa nhưng ghi nhận thất bại (`status != SUCCESS` hoặc `post_verified is False`), report có quyền phủ quyết toàn bộ log stdout, kết luận `is_success = False`.

## 4. Account Age & Cooling Period Gate (Gate 4c)
- **Quy tắc hoãn đăng video cho nick mới (10 ngày tuổi)**:
  - **Tik 1..Tik 4 (Row 1..4)**: Nick ca cũ đã trưởng thành -> Luôn đủ điều kiện (`eligible`), không áp dụng cooldown.
  - **Tik 5 & Tik 6 (Row 5 & 6) và các ca tạo mới sau này (Row >= 5)**:
    - Không được đăng video cho đến khi nick đủ 10 ngày tuổi kể từ ngày tạo (`NGÀY TẠO` trong `taikhoan_dat_v2_updated .xlsx`).
    - Với các nick hiện tại (tại thời điểm cấu hình 01/09/2026): Lấy mốc tối thiểu 10 ngày nữa là **11/09/2026** (`BENCHMARK_MIN_UPLOAD_DATE = date(2026, 9, 11)`).
    - Với các nick chưa tạo hoặc tạo mới sau này: Tính `created_date + 10 days`. Nếu ngày cho phép nhỏ hơn 11/09/2026 thì bắt buộc lấy mốc 11/09/2026:
      `min_upload_date = max(created_date + timedelta(days=10), date(2026, 9, 11))`
    - Nếu nick không ghi ngày tạo trong bảng master: Mặc định hoãn đến `2026-09-11`.
  - **Hành vi khi chưa đủ ngày**:
    - Preflight upload hook trả về `status: skipped` kèm lý do `account_cooling_period_until_<YYYY-MM-DD>`.
    - Tiến trình nuôi Feed vẫn chạy 100% đầy đủ qua tất cả các phiên.
    - Watchdog tổng kết tự động xếp vào nhóm Bỏ qua (`up_skipped`), không ghi nhận thành lỗi upload.

