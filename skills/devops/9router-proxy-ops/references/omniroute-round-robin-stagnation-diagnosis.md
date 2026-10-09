# OmniRoute Round-Robin & Account Stagnation Debugging

## 1. Hiện tượng
Cài đặt combo là `strategy: round-robin`, trong pool có hàng chục tài khoản Antigravity / OpenAI / OpenCode còn quota, nhưng khi client gọi request liên tục thì trên Dashboard/Logs thấy request bị dồn hầu hết vào đúng 1 account (ví dụ `duo***`), tạo cảm giác Round-Robin không hoạt động.

## 2. Các nguyên nhân cốt lõi trong code OmniRoute

### A. Batch Sticky Round-Robin (`stickyRoundRobinLimit > 1`)
- **Vị trí code:** `open-sse/services/combo.ts` & `open-sse/services/combo/rrState.ts` (`recordStickyRoundRobinSuccess`).
- **Cơ chế:** Khi `stickyRoundRobinLimit: 30` (hoặc N > 1), OmniRoute lưu `rrStickyTargets.set(comboName, { executionKey, successCount })`. Một account khi được chọn sẽ phải gánh đủ **30 request thành công liên tiếp** trước khi router tăng con trỏ `rrCounters` để xoay sang account tiếp theo.
- **Hệ quả:** Người dùng quan sát vài lượt gọi đầu sẽ thấy 100% request vào cùng một tài khoản.

### B. Session Stickiness theo Tin Nhắn Đầu (`disableSessionStickiness: false`)
- **Vị trí code:** `open-sse/services/combo/sessionStickiness.ts` (`applySessionStickiness`).
- **Cơ chế:** OmniRoute tính SHA-256 của tin nhắn user đầu tiên trong payload (`messages[0]`). Mọi request trong cùng conversation đó sẽ bị **ghim chặt (pinned)** vào account ban đầu để bảo toàn Prompt Cache upstream (Google Antigravity / Anthropic KV Cache).
- **Hệ quả:** Nếu client chat multi-turn (Hermes, Codex, Cursor), mọi turn kế tiếp đều đi qua 1 account duy nhất cho đến khi session TTL (15m) hết hạn hoặc account bị cạn headroom (< 0.15).

### C. Quá tải Semaphore Timeout (429) & Cooldown
- **Vị trí code:** `src/sse/services/auth.ts`, `domain_circuit_breakers`.
- **Cơ chế:** Khi 1 account bị nghẽn semaphore (`Semaphore timeout after 30000ms`), router sẽ tạm thời đưa account vào cooldown và skip qua các account khả dụng tiếp theo.

## 3. Lệnh tra cứu thực tế O(1) qua SQLite

Khi người dùng phản ánh nghi ngờ dồn tải, không đoán mò hay lý thuyết suông, inspect trực tiếp SQLite DB:
```bash
# 1. Kiểm tra config combo thực tế
curl -s http://127.0.0.1:20129/api/combos

# 2. Đếm phân bổ request thực tế theo account trong 30 phút gần nhất
python -c "
import sqlite3
con = sqlite3.connect('C:/Users/Kibe/.omniroute/storage.sqlite')
cur = con.cursor()
cur.execute('''
SELECT account, count(*), sum(tokens_in), sum(tokens_cache_read)
FROM call_logs
WHERE timestamp > datetime('now', '-30 minutes')
GROUP BY account
ORDER BY count(*) DESC
''')
for r in cur.fetchall():
    print(r)
"
```

## 4. Cách cấu hình True Round-Robin (1:1)

Trên OmniRoute Dashboard (`http://localhost:20129`) -> **Combos** -> Edit combo mục tiêu:
1. Đặt **Sticky Round-Robin Limit** = `1` (hoặc `0`).
2. Tick bật **Disable Session Stickiness** (lưu ý: chấp nhận miss prompt cache để chia đều từng request).
3. Lưu combo.
