# Cohort Manifest Regeneration Digest Mismatch (Case 58 / LOCK-05)

## 1. Hiện tượng & Triệu chứng
Khi cron nuôi feed (`run_tiktok.py --mode multi-machine-feed-session`) đang chạy, các máy bỗng nhiên đồng loạt dừng phiên với thông báo lỗi:
- `Lý do: cohort artifact assignment digest mismatch` (hoặc `ValueError: cohort artifact assignment digest mismatch`)
- Trạng thái Telegram alert: `🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ`.
- Máy dừng ở màn hình Home / Feed mà không thao tác tiếp.

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
- `run_tiktok.py --mode multi-machine-feed-session` được khởi chạy với 2 tham số:
  `--cohort-artifact <path>/cohort-v1-<hashA>.json`
  `--assignment-manifest <path>/manifests/<day>/assignment-v1-<hashA>.json`
- `load_cohort_plan(artifact, assignment_manifest=...)` trong `cohort_watchdog.py` kiểm tra:
  `sha256(assignment_manifest_from_disk) == plan.manifest_digest`
- Nếu giữa chừng có script (như `hermes_taikhoan_sync_cron.py`) chạy đồng bộ file `taikhoan_run_safe.xlsx` và thực hiện:
  - `shutil.rmtree` thư mục `manifests/<day>` và `cohorts/<day>`.
  - Gọi `tiktok_picker.py` sinh manifest mới `assignment-v1-<hashB>.json`.
- Khi tiến trình feed của các máy (Worker threads) nạp manifest từ disk, nội dung trên disk đã bị thay thế thành `hashB` trong khi `--cohort-artifact` của process đang giữ `manifest_digest = hashA`.
- Kết quả: `digest != plan.manifest_digest` phát sinh `cohort artifact assignment digest mismatch`, huỷ toàn bộ phiên chạy của các máy còn lại trong batch.

## 3. Quy tắc an toàn bắt buộc (Invariants)
1. **Tuyệt đối không xoá (rmtree) thư mục manifests/cohorts trong ngày khi đang có tiến trình feed active**:
   - Kiểm tra `run_tiktok.py` / `multi-machine-feed-session` có đang chạy không trước khi can thiệp tái tạo manifest.
2. **Ghi đè/Tái tạo manifest phải an toàn không huỷ file cũ (Non-destructive versioning)**:
   - Giữ nguyên file manifest cũ cho đến khi phiên kết thúc; chỉ cập nhật pointer `ACTIVE.json` sang manifest mới cho các phiên kế tiếp.
3. **Phản hồi người dùng khi gặp alert đính kèm**:
   - Luôn kiểm tra context ảnh/alert Telegram (`cache/images`, `device-locks`, `log.jsonl`) trước khi hỏi lại người dùng, tránh hỏi lại thông tin đã gửi trong tin nhắn đính kèm.
