# Quy tắc kế thừa Device Lock khi Follow Runner được gọi từ Feed Hook

## Bối cảnh & Hiện tượng
- Khi `multi_machine_feed_session.py` (trong `tiktok-luot nuoi acc`) chạy lướt feed thành công trên một máy, nó gọi subprocess sang `tiktok-follow` qua lệnh:
  `python -m follow_runner.run_follow --machine N --config ... --account-row-index R --skip-identity-verify`
- Trong khi đó, tiến trình cha `multi_machine_feed_session.py` đang nắm giữ `device_lock` trên thiết bị `machine_N.lock.json` với `project: "tiktok-luot nuoi acc"`.

## Nguyên nhân lỗi Follow Success = 0
- Khi `run_follow.py` khởi động preflight gate, nó gọi `acquire_device_lock(machine=N, project="tiktok-follow", user_authorized=False)`.
- Hàm này phát hiện file lock của tiến trình cha và ném ngoại lệ `DeviceLockNeedsUserDecision`.
- Nếu `run_follow.py` bắt ngoại lệ và thoát ngay với mã lỗi 2 (`exit_code: 2`), toàn bộ các máy chạy feed hook sẽ bị fail preflight, dẫn đến kết quả `Follow Success: 0` trên toàn farm.

## Giải pháp chuẩn hóa
Trong `follow_runner/run_follow.py`, tại khối xử lý preflight lock:
```python
try:
    acquire_device_lock(
        machine=args.machine, serial=row.serial,
        project="tiktok-follow", user_authorized=False,
    )
except DeviceLockNeedsUserDecision as exc:
    parent_project = str(exc.owner.get("project") or "").strip().lower()
    if args.skip_identity_verify and parent_project in ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session"):
        pass  # Được phép kế thừa lock từ tiến trình cha đang chạy phiên feed
    else:
        print(f"BLOCKED: [device-lock] máy {args.machine} ({row.serial}) đang được "
              f"User khóa bởi {exc.owner.get('project', '?')} (pid "
              f"{exc.owner.get('pid', '?')}) — safe-skip, KHÔNG can thiệp.",
              file=sys.stderr)
        return 2
```

## Kiểm thử & Xác nhận
1. Chạy test CLI: `pytest follow_runner/tests/test_cli.py` đảm bảo không bị chặn bởi device lock.
2. Chạy live canary với flag `--skip-identity-verify` trên máy đang có lock của parent process: kiểm tra subprocess mở TikTok và thực hiện flow follow bình thường.
