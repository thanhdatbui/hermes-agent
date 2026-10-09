# Triage Lỗi Upload Hook VETO Khi Auto-Advance Nhảy Số Video (2026-09-16)

## 1. Hiện tượng & Triệu chứng
- Sau ca chạy nuôi acc kèm upload video cuối phiên (Ca 1 / Ca 2 / Ca 3 / Ca 4), Watchdog (`feed_session_watchdog.py`) báo cáo tỷ lệ lỗi upload cao bất thường (ví dụ: 73/80 máy fail, chỉ 3 máy success).
- Tuy nhiên, kiểm tra đối soát ground truth từ file workbook (`TikN.xlsx`) và thư mục runtime `D:/CodexRuntime/tiktok-video/runs`:
  - Hầu hết các máy (72/80 máy) đều có `report.json` với `status: SUCCESS`, `post_verified: True`.
  - Cột `Video Đã Đăng` trong workbook đã nhảy số thành công.
  - Video thực tế đã được đăng lên kênh TikTok và xác minh tile trên lưới Profile.

## 2. Nguyên nhân gốc rễ
1. **Cơ chế Auto-Advance trong `Tiktok-video` (`state_machine.py`):**
   - Trước khi upload, feed runner đọc workbook và suy đoán số video cần đăng tiếp theo là $N$ (truyền CLI `--video-number N`).
   - Khi chạy workflow, script upload kiểm tra fingerprint SHA-256 trên ledger; nếu phát hiện video $N, N+1...$ đã từng được đăng hợp lệ trước đó, script tự động kích hoạt `_auto_advance_verified_videos()`:
     `[AUTO-ADVANCE] Skipped X verified video(s); new_video_number=M (was N)`
   - Script push video $M$ lên kênh TikTok, xác minh thành công và ghi vào `report.json`: `"video_number": M`, `"status": "SUCCESS"`.
2. **Bẫy so khớp cứng (Hard Equality VETO) trong Feed Session Hook:**
   - Trong `multi_machine_feed_session.py`, hook xác minh kiểm tra report với điều kiện:
     `and int(rep_video_num) == int(next_video)`
   - Khi có Auto-Advance ($M \ne N$), biểu thức trả về `False`.
   - Cờ `report_veto_failed = True` kích hoạt quyền phủ quyết an toàn (VETO), ép kết quả thành công thành thất bại (`is_success = False`), ghi nhãn `reason: "post_verification_failed"`.
   - Kết quả: 100% các máy có Auto-Advance bị Watchdog gom vào nhóm lỗi kịch bản.

## 3. Giải pháp chuẩn & Bảo vệ an toàn (Hardened Regex Validation)
Không kiểm tra substring lỏng lẻo (dễ bị bypass bởi log rác), mà phải phân giải cấu trúc chặt chẽ từ log stdout của `state_machine.py`:

```python
actual_video_num = int(rep_video_num) if rep_video_num is not None else None
auto_advance_matched = False
if actual_video_num is not None and actual_video_num > int(next_video):
    aa_match = re.search(
        r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new_video_number=(\d+)\s+\(was\s+(\d+)\)",
        stdout,
    )
    if aa_match:
        aa_new, aa_was = int(aa_match.group(1)), int(aa_match.group(2))
        if aa_new == actual_video_num and aa_was == int(next_video):
            auto_advance_matched = True

is_video_num_valid = (
    actual_video_num is not None
    and (
        actual_video_num == int(next_video)
        or auto_advance_matched
    )
)
```

Đồng thời cập nhật số video thực tế vào ledger:
```python
success_recorded = _ShiftUploadLedger.complete_success(
    deadline_config,
    logical_day=logical_day,
    machine=account.machine,
    row=account.account_row_index,
    account_id=account_id,
    video_number=effective_video_number,  # Sử dụng actual_video_num đã verified
    run_id=exact_run_id,
    token=reservation_token,
)
```

## 4. Quy trình đối soát & Backfill Ledger khi xảy ra sự cố
1. **Kiểm tra `report.json` và workbook `TikN.xlsx`:**
   - Quét nhanh `runs/run_<serial>_<date>_*/report.json` để xác định số lượng máy thực sự `SUCCESS`.
2. **Backfill ledger `shift_upload_history.json`:**
   - Chuyển các entry đang ở trạng thái `launched` thành `success` nếu đã có `report.json` thành công tương ứng.
3. **Chạy lại Watchdog:**
   - Xóa key phiên tương ứng khỏi `feed_session_reported.json` để Watchdog đối soát lại ledger và phát báo cáo số liệu chuẩn.
