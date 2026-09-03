# Recovery 5-Step Protocol (Canonical)

## B1 — Inspect (Trích xuất hiện trường)
```bash
python D:/Taadaa/tools/inspect_machine.py <machine_id>
```
Lấy: screenshot, focus app, XML UI, device state, log error, step dừng.

## B2 — Root Cause (Đọc code đích danh)
Dựa vào `flow_file` trong alert → `read_file` đúng file flow phụ trách (không grep, không find).
Ví dụ: `feed_swipe_smoke.py`, `device_prepare.py`, `follow_engine.py`, `benign_popup.py`.

## B3 — Patch Script (Vá code tự phục hồi)
Thêm logic auto-recovery vào script:
- Detect popup/màn hình kẹt mới → thêm selector vào `benign_popup.py`
- Detect focus lost / app crash → thêm retry/ relaunch trong flow chính
- **Quy tắc**: Patch phải cover toàn farm (80-160 máy), không chỉ máy đang lỗi.

## B4 — Canary Verification (Live test máy N)
Chạy lệnh `canary_cmd` từ alert (2 swipes / 2 action) trên đúng máy bị lỗi:
```bash
# Feed session
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 42 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run

# Follow
python -m follow_runner.run_follow --machine 42 --config config.yaml --account-row-index 1 --skip-identity-verify

# Reg
python D:/Taadaa/Tiktok_Reg/_run_all_targets.py
```

## B5 — Báo cáo kết quả
Gửi kết quả gọn: Tình trạng → Cách xử lý → Kết quả Canary (Pass/Fail + chi tiết).