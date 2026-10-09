# OmniRoute Nested Combo Semaphore Timeout & Backend Build-Restart Runbook

## Bối Cảnh & Hiện Tượng
Khi cấu hình Combo lồng nhau trong OmniRoute (ví dụ: Parent `omni-worker` Priority -> Child `ag-gemini-pool-3` Round-Robin 16 Pro accounts -> Child `ag-gemini-free-pool` P2C 70 Free accounts):
- User yêu cầu: Khi 1 tài khoản Pro bận/nghẽn slot (`max_concurrent = 2`), router phải **tràn tải (spillover) sang các tài khoản Pro khác trong cùng nhánh** trước khi cascade rớt xuống nhánh Free hoặc nhảy sang model khác.
- Hiện tượng lỗi: Request bị giữ 30-31 giây rồi trả `429: Semaphore timeout after 30000ms for antigravity:<id>`. Sau đó parent combo vội vàng rớt xuống Free pool hoặc Claude fallback (báo `ALL_TARGETS_SKIPPED` hoặc 503/429 upstream).

## 3 Điểm Nghẽn Cốt Lõi (Root Causes)

### 1. `maxGlobalAttempts` của Child Combo quá nhỏ so với số Target
- **Nguyên nhân**: Child combo có 16 targets nhưng `config.maxGlobalAttempts` trong DB chỉ đặt là `5`.
- **Hậu quả**: Router chỉ thử qua tối đa 5 accounts. Nếu cả 5 đều bận hoặc lỗi nhẹ, child combo coi như exhausted và trả `null` về parent combo, khiến parent combo cascade non xuống Free pool dù 11 accounts Pro còn lại vẫn rảnh.
- **Khắc phục**: Đặt `maxGlobalAttempts >= số lượng target` (ví dụ: 16 targets -> set `20` để có buffer 1-2 lần retry).

### 2. Bug Source `chatCore.ts`: `isCombo` bị `false` trên đường Nested Combo Execute
- **Nguyên nhân**: Trong `open-sse/handlers/chatCore.ts`:
  ```ts
  const releaseAccountSemaphore =
    (claimedPreAcquiredRelease ? preAcquiredRelease : null) ??
    (accountSemaphoreKey && accountSemaphoreMaxConcurrency != null
      ? await acquireAccountSemaphore(accountSemaphoreKey, {
          maxConcurrency: accountSemaphoreMaxConcurrency,
          timeoutMs: isCombo ? 1000 : undefined, // <-- BUG: nested execution thì isCombo=false
          signal: streamController.signal,
        })
      : () => {});
  ```
  Khi gọi qua combo con với `nestedComboMode: "execute"`, cờ `isCombo` trong context của `handleChatCore` bị đánh giá là `false`. Kết quả là `timeoutMs = undefined`, `acquireAccountSemaphore` dùng giá trị mặc định `30000ms`.
- **Khắc phục**: Sửa `timeoutMs: 1000` trực tiếp tại block này để mọi account semaphore acquisition trong luồng nội bộ đều fail-fast trong 1 giây khi slot bị chiếm đủ 2/2, nhả target để router thử account Pro kế tiếp.

### 3. Build & Reload Production Seam (Next.js Standalone)
- **Cơ chế**: OmniRoute chạy bằng standalone server (`scripts/dev/run-next.mjs start` / `.next/standalone/server.js`).
- **Bẫy vận hành**: Chỉ sửa code `.ts` hoặc sửa DB mà **không build backend** thì process đang chạy (`:20129`) vẫn chạy bundle cũ và tiếp tục dính timeout 30s.
- **Quy trình Reload chuẩn**:
  1. Kiểm tra build backend: `npm run build:backend` (chạy script `build-next-isolated.mjs`, không build full UI).
  2. Kill process Next runner đang giữ port `20129` (tìm qua `netstat -ano | grep 20129` hoặc `Get-CimInstance Win32_Process`).
  3. Khởi động lại: `node scripts/dev/run-next.mjs start` (hoặc qua launcher background).
  4. Kiểm tra health: `curl http://127.0.0.1:20129/api/health` -> HTTP 200.

## Dấu Hiệu Nhận Biết Fix Thành Công
1. Log `call_logs`: `Semaphore timeout after 30000ms` biến mất hoàn toàn, chỉ còn `Semaphore timeout after 1000ms` khi acc bận 2/2 slot.
2. Request được điều phối đều: Các acc Pro khác (ví dụ: `toloan`, `lelinh`, `dokieu`, `dangmai`) nhận request và trả về `200 OK` liên tục.
3. Không bị cascade non xuống Free pool hay Claude khi nhánh Pro vẫn còn tài khoản rảnh quota.
