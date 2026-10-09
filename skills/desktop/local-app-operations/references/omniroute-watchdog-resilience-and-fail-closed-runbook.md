# OmniRoute Fail-Closed Proxy & Watchdog Resilient Supervision Runbook

## 1. Ngữ cảnh & Bài học thực tế

Trong phiên vận hành ngày 28/09/2026:
- Khi pool tài khoản gặp lỗi upstream (401 Unauthorized do token expired, 403 Forbidden do Sentinel/Turnstile, 429 Rate Limit): các lỗi này thuộc phạm vi request/target routing.
- Watchdog cũ chỉ gọi HTTP `GET /api/health` với timeout 15s. Khi Node event loop bị chậm do gánh nhiều request burst hoặc concurrency cao, `/api/health` phản hồi trễ >15s liên tiếp 8 lần dẫn đến việc watchdog tưởng lầm server sập và tự động kill process Node, gây gián đoạn toàn bộ các phiên làm việc đang chạy (đặc biệt là Codex streaming sessions).
- Cấu hình proxy cũ cho phép fail-open (`PROXY_FAIL_OPEN=true`), dẫn đến nguy cơ rò rỉ real-IP của host khi proxy gặp sự cố.

---

## 2. Chuẩn hóa Fail-Closed Proxy

Trong file cấu hình môi trường `.env` (`%APPDATA%\omniroute\.env` và `C:\Users\Kibe\OmniRoute\.env`):
```ini
# Bắt buộc fail-closed: từ chối request nếu proxy lỗi, cấm fallback IP trực tiếp
PROXY_FAIL_OPEN=false
OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK=false
```

---

## 3. Kiến trúc Watchdog 2 Lớp (Process Liveness vs Health Degraded)

Trong `omniroute_watchdog.ps1`:
1. **Liveness Check (`Test-OmniRouteProcessAlive`)**:
   - Quét tiến trình `node.exe` sở hữu command line chứa `run-next.mjs`.
   - Kiểm tra listener cổng 20129 thông qua `Get-NetTCPConnection -LocalPort 20129 -State Listen`.
2. **Health Check (`Test-OmniRouteAlive`)**:
   - Gọi `GET http://127.0.0.1:20129/api/health` với timeout 15s.
3. **Quyết định Restart**:
   - Nếu `/api/health` lỗi nhưng **process và listener port 20129 vẫn còn sống**: Chỉ ghi log `health_degraded`, reset counter failure về 0, **TUYỆT ĐỐI KHÔNG RESTART**.
   - Chỉ restart khi và chỉ khi **tiến trình hoặc port 20129 thực sự biến mất/sập hẳn** liên tục qua ngưỡng thất bại (`$MaxConsecutiveFailures`).

---

## 4. Kỷ luật Nạp RAM & Lưu Trữ Mã Nguồn

1. **Nạp RAM tiến trình**: Khi sửa code `.ps1`, tiến trình PowerShell chạy ngầm không tự cập nhật code mới. Bắt buộc phải tìm PID cũ, kill tiến trình và khởi động lại phiên bản headless mới:
   ```powershell
   Stop-Process -Id <OLD_PID> -Force
   Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\Kibe\AppData\Roaming\omniroute\omniroute_watchdog.ps1"' -WindowStyle Hidden
   ```
2. **Repo-First Documentation**: Bắt buộc sao chép bản chuẩn hóa của script watchdog vào mã nguồn repo (`scripts/ops/omniroute_watchdog.ps1`) và cập nhật tài liệu hướng dẫn (`docs/deployment/UPDATE_RUNBOOK.md`), sau đó commit/push vào Git repository.
