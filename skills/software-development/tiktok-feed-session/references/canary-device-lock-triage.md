# Canary Test & Device-Lock Triage Workflow

## 1. Lệnh Chạy Canary Test Chuẩn (Single/Multi Machine)
Khi chạy Canary test xác thực tính năng hoặc kiểm tra máy lẻ (ví dụ Máy 3, Row 1, 2 Recovery Swipes):
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 3 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

## 2. Tình Huống: `skipped-device-locked` / `manual-needed`
Nếu lệnh trả về:
- `Status: manual-needed`
- `multi-machine-feed-session has locked machine(s) requiring operator decision`
- `stop_reason: device lock active: path=C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json pid=<PID>`

### Nguyên nhân:
Một cron job toàn farm (hoặc batch job đa máy) đang chạy (`run_tiktok.py --mode multi-machine-feed-session`) và đang giữ device lock của máy mục tiêu.

### Quy trình xử lý bắt buộc (CẤM PHÁ VỠ HỆ THỐNG):
1. **Tuyệt đối CẤM:**
   - KHÔNG xóa file `.lock.json` bằng tay.
   - KHÔNG dùng `taskkill` để hủy tiến trình batch đang chạy của farm.
2. **Kiểm tra trạng thái batch hiện tại:**
   - Kiểm tra PID: `tasklist | grep <PID>`
   - Xem tiến độ batch: đếm các máy đã hoàn thành trong log live:
     `grep -c "feed-session-smoke" "D:/Taadaa/runtime/kibe/live/.../log.jsonl"`
3. **Chờ giải phóng lock:**
   - Khi batch job kết thúc, tiến trình cha sẽ tự động thu dọn và giải phóng lock files trong `C:\Users\Kibe\.codex\device-locks\`.
   - Kiểm tra xác nhận lock của máy mục tiêu đã được giải phóng:
     `ls -la "C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json"`
4. **Tái thực thi Canary Test:**
   - Chạy lại lệnh PowerShell ban đầu ngay sau khi lock được nhả.
5. **Nghiệm thu kết quả Canary:**
   - Đọc và kiểm tra `summary.txt` tại artifact root:
     * `final_status: success`
     * `total_swipes_completed`: đủ số lượng yêu cầu (vd 2/2)
     * Checkpoint popup: `dismissed: True`
     * Preflight & verify profile thành công
     * `cleanup_close_all: success`
