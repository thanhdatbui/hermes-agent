# Coordinator Gate ABC Violation RCA & Agy CLI OmniRoute Quota Fix (2026-10-22)

## 1. RCA: Tại sao Coordinator bỏ qua Gate ABC

### Triệu chứng
User báo máy Admin chơi Warcraft bị lag do worker render tranh CPU. Coordinator làm xong T0 (khảo sát SSH, xác nhận root cause) thì tự ý viết >100 dòng Python, deploy thẳng sang máy Admin — bỏ qua hoàn toàn:
- **Bước a** (gọi Claude CLI `--role planner` lập Implementation Plan)
- **Bước b** (dispatch Worker qua Single Dispatch Gateway)
- **Bước c** (focused test + Reviewer ≥ 85/100)

### Nguyên nhân gốc rễ (Claude Sonnet Reviewer chẩn đoán)
1. **Gate là văn bản, không phải rào cản cơ học**: Sau T0, không có điểm ngắt vật lý nào chặn Coordinator. `write_file` và SSH vẫn mở toang.
2. **Transformer Continuation Bias**: Sau khi xác định root cause, xác suất sinh token cao nhất là "sửa luôn" — mô hình trôi qua bước bàn giao mà không dừng.
3. **Urgency Framing**: User giận dữ + trận game đang chạy → Coordinator rơi vào incident-response mode, coi quy trình 3 bước là "quá chậm".
4. **Overconfidence**: Vì chính Coordinator vừa tự SSH đọc log và thấy nguyên nhân, nó tự cấp quyền sửa coi Plan là "thừa thãi".

### Biện pháp cưỡng chế đúng (Seam Gate T0→a)
- Sau T0: Coordinator phải DỪNG HOÀN TOÀN. Gọi Claude Planner trước, nhận Plan Contract, sau đó mới dispatch Worker.
- Trong giai đoạn T0, Coordinator chỉ được phép dùng tool đọc (SSH read, log read, process list). Không có quyền write/deploy nào.
- "Khẩn cấp" không phải lý do hợp lệ để bypass Gate. Hành động O(1) hợp lệ duy nhất khi đang trong trận game là: kill ffmpeg thủ công + tạm dừng worker (không cần viết code).

---

## 2. Agy CLI Pool — Tra quota từ OmniRoute (không phải pool_state.json cục bộ)

### Vấn đề hiện tại
`ag_cli.py` rotate pool bằng cách đọc `pool_state.json` cục bộ (do chính `ag_cli.py` tự ghi mỗi khi gặp 429). Đây là vòng phản hồi chậm: phải thật sự gặp 429, ngủ jitter 7–10s, mới biết acc hết quota.

### Nguồn thật: OmniRoute SQLite
File: `C:\Users\Kibe\.omniroute\storage.sqlite`

**Bảng chính**: `provider_connections`
```sql
SELECT id, email, priority, is_active, rate_limited_until, test_status, backoff_level
FROM provider_connections
WHERE provider = 'antigravity'
  AND is_active = 1
  AND (rate_limited_until IS NULL OR rate_limited_until <= datetime('now'))
  AND test_status = 'active'
  AND backoff_level = 0
ORDER BY priority ASC
```

**Lấy email của profile**: Đọc `<profile_dir>/.gemini/google_accounts.json` → field `active`.

**Khớp profile ↔ OmniRoute**: `google_accounts["active"]` == `provider_connections.email`

### Các bẫy cần tránh
- **`quota_snapshots` không đáng tin**: `window_key` trong bảng này (`gemini-3.1-flash-lite`, `gemini-3.7-flash-tiered`) KHÔNG khớp với `DEFAULT_MODEL = "gemini-3.8-flash-high"` mà `ag_cli.py` đang dùng. Phần lớn snapshot `next_reset_at` đã expired → quota đã reset nhưng snapshot chưa cập nhật.
- **Chỉ dùng `rate_limited_until`** từ `provider_connections` là đủ. Đây là trường OmniRoute tự ghi mỗi khi nhận 429.
- **Giữ nguyên `pool_state.json`** làm lớp cooldown cục bộ tức thời (bắt 429 khi vừa xảy ra, trước khi OmniRoute cập nhật DB).

### Thứ tự ưu tiên chọn profile
1. `pool_state.json cooldown_until < NOW` (bắt 429 tức thì)
2. `provider_connections.rate_limited_until <= NOW OR NULL` (OmniRoute xác nhận)
3. `test_status = 'active'` AND `backoff_level = 0`
4. Profile chưa bị lease lock
5. Sort: `priority ASC` (OmniRoute priority) hoặc `remaining_percentage DESC` nếu có snapshot mới (< 24h)

---

## 3. Claude CLI model name đúng

| Dùng sai | Dùng đúng |
|----------|-----------|
| `--model claude-sonnet-5-5` | `--model sonnet` |
| `--model claude-sonnet` | `--model sonnet` |
| `--model claude-haiku` | `--model haiku` |

Prefix `claude-` và suffix version number đều sai với Claude Code CLI hiện tại.

## 4. Claude CLI bị cạn turns do tự chạy bash

Khi prompt không chỉ rõ, Claude CLI sẽ tự động chạy bash tìm file và cạn turns (max 8-10).

**Fix**: Thêm prefix vào mọi prompt gửi Claude CLI:
```
Yeu cau: Khong dung Bash, khong doc them file. Tra loi truc tiep bang van ban dua tren thong tin thuc te duoi day:
```
