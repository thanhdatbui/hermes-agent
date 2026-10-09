# Follow mode tracking + fail-safe (case máy 31 @phannhung1710, 2026-09-13)

## Báo cáo cho user Việt
- Trả lời bằng **tiếng Việt ngắn gọn**: Mục đích -> Kết quả -> Blocker.
- CẤM báo cáo dài toàn tiếng Anh khi user là người Việt (user đã chửi vì việc này).
- Mọi báo cáo follow BẮT BUỘC ghi `mode1_followed_count` và `mode2_followed_count`
  (trong `details` của `FOLLOW_RESULT`): `mode2=0` = lỗi search anchor,
  `mode1=N` = số bù qua search trực tiếp.

## Mode 2 anchor no_video
- Safe-skip, ghi `details["mode2_skip_reason"] = f"anchor @{uid} không có video"`,
  giữ `status=OK` để Mode 1 chạy bù — CẤM biến thành MANUAL_REVIEW đứng cả phiên.
- Commit `103ecfe` (tiktok-follow): SessionResult.mode1_followed/mode2_followed,
  details count, dirty failed=True bảo toàn.

## cleanup_after_result (run_follow.py)
- Chỉ normalize `failed=False` khi strict-clean (`is_strict_clean==True`).
- Dirty (`True/None/missing`): bảo toàn `failed=True` + gắn `follow_failed=True`.
- UI-59 fail-safe close vẫn đóng app về HOME trên mọi exit path.
- Test align: case49 dirty/missing dùng `assert_called_once()`, không phải `assert_not_called()`.

## Worker discipline
- CẤM sửa lố ngoài Patch Contract (vụ `if True` thay `if is_mock_adapter`):
  phát hiện là revert ngay, chỉ giữ hunk đã duyệt.
- Worker timeout 600s: contract đã khảo sát 100% thì lượt sau chỉ ghi file + test,
  cấm grep/scan rộng lại từ đầu.
