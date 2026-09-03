# Canonical TikTok batch + avatar evidence

## Canonical launcher invariant

Tik1/Tik2/TikN và account row 1/2/N phải dùng cùng entrypoint đã chạy chuẩn. Chỉ thay workbook/data/row/config qua tham số. Không tạo `tik2-live-launcher.ps1`, runner tạm, hoặc shell loop để thay flow canonical.

Minimum launch evidence:

- `canonical_script`: repo path của `run_tiktok_upload_batch.ps1`.
- `data_path`: workbook thực tế (ví dụ `Tik2.xlsx`).
- `host_config`: host config quyết định `workbook_root`/machine range.
- `MaxParallel`: giới hạn worker thực tế.
- batch directory, `summary.csv`, từng machine log/report.

Dài hơn 5 phút phải chạy background với notify-on-complete. Nếu foreground timeout hoặc launcher crash, trước retry phải:

1. scan real `python.exe/pythonw.exe` command lines; wrapper shell không tính;
2. đọc summary/checkpoint/receipt theo từng máy;
3. phân biệt `NOT_LAUNCHED`, `SKIPPED_LOCKED`, `MANUAL_REVIEW`, `FAILED`, `SUCCESS`;
4. không restart mù, không tạo launcher bù.

`SUCCESS` chỉ là claim khi có `status=SUCCESS`, `post_verified=true`, `post_submission_state=ACCEPTED`; với các account/workbook nhạy cảm còn cần evidence độc lập theo policy (profile/accepted proof). Workbook increment hoặc process exit không đủ.

## Runtime version gate

Nếu PowerShell báo version package khác với cùng executable khi chạy từ shell, probe đúng executable bằng:

```bash
env -u PYTHONPATH -u PYTHONHOME "<venv>/Scripts/python.exe" -c "import importlib.metadata as m; print(m.version('automation-core'))"
```

PowerShell có thể nạp user-site của Hermes trước site-packages của venv. Canonical launcher phải isolate môi trường (`PYTHONNOUSERSITE=1`, set `PYTHONPATH` có chủ đích) rồi mới đọc version gate. Không nới expected version theo lỗi chưa xác minh.

## Avatar contract

`ENSURE_AVATAR` chạy sau video path `UPDATE_WORKBOOK` trong workflow bình thường. Nó:

1. mở/verify Profile;
2. phân loại avatar bằng semantic XML + screenshot visual metrics;
3. chỉ `MISSING` mới được mở sửa hồ sơ và upload `avatar.jpg` đúng folder;
4. `PRESENT` → `SKIPPED_EXISTING_AVATAR`;
5. `UNKNOWN` → `SKIPPED_AVATAR_STATE_UNKNOWN`, không upload mù;
6. upload phải refresh MediaStore, chọn tile bằng identity/visual match, save và verify.

`--force-avatar-upload` không phải auto-detect; nó chỉ cho phép thay avatar khi machine nằm trong `--force-avatar-machines`. Không dùng force cho toàn batch nếu user chỉ nói “avatar đang thiếu” mà chưa có target/data scope rõ.

Quan trọng: batch report có `avatar_status=null` nghĩa là worker chưa ghi nhận avatar state — thường vì fail trước `ENSURE_AVATAR`. Nó không chứng minh avatar đã upload hoặc đã được kiểm tra. Muốn kết luận Tik2 avatar đã xử lý, cần report/checkpoint có `ENSURE_AVATAR` và status cụ thể (`UPLOADED_VERIFIED`, `SKIPPED_EXISTING_AVATAR`, hoặc `SKIPPED_AVATAR_STATE_UNKNOWN`).

## Incident pattern từ batch thực tế

- Launcher custom crash ở `WaitForExit` có thể để 66 child worker đã chạy nhưng 3 máy chưa launch; phải dùng per-machine logs/reports, không coi launcher exit là toàn batch result.
- Preflight/background batch có thể bị foreground timeout; chạy canonical launcher background và chờ đủ batch.
- Lock release chỉ được làm với explicit user authorization, exact allowlist, dead owner verification và guarded core API; không xóa lock file thô.
