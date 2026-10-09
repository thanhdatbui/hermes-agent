# OmniRoute 16GB Heap, 120s Lockout Cooldown, và Decoupled Watchdog Architecture (2026-10-04)

## 1. Bối cảnh Sự Cố (Root Cause Analysis: V8 OOM & Cooldown Lockout Trap)
Ngày 04/10/2026, hệ thống OmniRoute trên cổng `:20129` gặp 2 sự cố gián đoạn liên tiếp:

### Sự cố 1 (12:49): Sập do tràn V8 Heap Memory (Exit Code 0xC0000409)
1. **Payload khổng lồ:** Bot Hermes tích lũy context lớn (440–700+ messages kèm 28 tool schemas, payload > 250k tokens).
2. **Proxy chập chờn:** Một số tài khoản Pro gặp lỗi proxy rớt (`http://test.taadaa.click:5113`, `5115`, `5135` trả 503).
3. **Bẫy Lockout Cooldown 600s:**
   Cấu hình runtime `modelLockout.baseCooldownMs` bị đặt ở mức `600000ms` (10 phút). Khi dính lỗi, toàn bộ 20 tài khoản Pro bị nhốt vào cooldown 10 phút, báo lỗi:
   `antigravity | hard-bound connection <id> unavailable; refusing sibling selection`
4. **Vết dầu loang sang Free Pool (79 accounts):**
   Khi dàn Pro cạn slot, router tràn sang `ag-gemini-free-pool`. Router duyệt tuần tự qua 79 tài khoản Free, clone request nặng 700 messages lặp lại qua RAM cho 4-5 request song song $\rightarrow$ bộ nhớ Node vượt trần 8GB, gây OOM crash.

### Sự cố 2 (17:55): Watchdog chết theo phiên AI Assistant
Watchdog chạy từ terminal của AI Assistant (task background). Khi session idle sau 4 tiếng, hệ thống tự động dọn dẹp task và kill toàn bộ cây tiến trình (Watchdog $\rightarrow$ Node.js), làm mất hoàn toàn dịch vụ.

---

## 2. Giải Pháp Khắc Phục Triệt Để (Structural Remedy)

### A. Tăng Trần RAM Heap 16GB cho Node.js
Trong `omniroute_watchdog.ps1`:
```powershell
# Nâng từ 8192 lên 16384 (16GB)
$nodeArgs = @(
    "--max-old-space-size=16384",
    ".build\next\standalone\server.js"
)
```

### B. Hạ Bẫy Cooldown Lockout về Chuẩn 120s (2 phút)
Cập nhật qua API `PATCH /api/settings` và ghi vĩnh viễn vào `C:/Users/Kibe/.omniroute/storage.sqlite` (bảng `key_value`, namespace `settings`, key `modelLockout`):
```json
{
  "modelLockout": {
    "enabled": true,
    "errorCodes": [403, 404, 429, 502, 503, 504],
    "baseCooldownMs": 120000,
    "maxCooldownMs": 600000,
    "maxBackoffSteps": 5,
    "useExponentialBackoff": true
  }
}
```
*Hiệu quả:* Khi proxy chập chờn, tài khoản Pro hồi sinh sau 2 phút thay vì bị giam 10 phút, ngăn chặn tràn tải sang dàn Free.

### C. Nâng Tải Đồng Thời Dàn Pro (maxConcurrent = 5)
Cập nhật bảng `provider_connections` trong `storage.sqlite`: nâng `maxConcurrent` cho toàn bộ 20 tài khoản Pro từ `3` lên `5` (tổng tải đồng thời đạt 100 slots).

### D. Tách Rời Vĩnh Viễn Watchdog (WMI Decoupling)
Khởi động Watchdog độc lập qua Windows Management Instrumentation:
```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = 'powershell.exe -ExecutionPolicy Bypass -File C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1'
}
```
Tiến trình mẹ là `WmiPrvSE.exe` (Dịch vụ Windows), hoàn toàn không bị ảnh hưởng khi đóng IDE, terminal hay AI Assistant timeout.

---

## 3. Bộ Kiểm Thử Tự Động Fail-Closed (`tests/test_omniroute_combos.py`)
Bắt buộc có các bài test xác nhận:
1. `settings_backup.json` chứa `baseCooldownMs == 120000`, `maxCooldownMs == 600000`, `maxBackoffSteps == 5`.
2. Live API `GET http://127.0.0.1:20129/api/settings` trả về HTTP 200 và cấu hình lockout 120s.
3. SQLite persistence fail-closed: `assert OMNIROUTE_DB.exists()`, query `key_value` xác nhận `modelLockout` lưu trữ đúng chuẩn.
4. Telemetry `call_logs` bắt buộc ghi nhận trạng thái 200 và account label hợp lệ.
