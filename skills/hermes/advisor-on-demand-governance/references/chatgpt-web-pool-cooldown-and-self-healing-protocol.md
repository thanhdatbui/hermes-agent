# ChatGPT-Web Pool Cooldown and Self-Healing Protocol (OmniRoute gpt-web-sol)

## 1. Bản Chất 2 Dạng "Acc Lỗi / Acc Chết" Trên ChatGPT-Web

Trong hạ tầng OmniRoute nối với Web reverse proxy của OpenAI (`chatgpt-web`), tài khoản không bị xóa/die vĩnh viễn mà rơi vào 2 trạng thái kỹ thuật:

1. **Lỗi 401 Auth Failed (Hết hạn phiên cookie)**:
   - Log: `[401]: ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie from chatgpt.com.`
   - Cơ chế: Cookie phiên hết hạn. Connection này hoàn toàn mất quyền gọi API chatgpt.com cho đến khi đăng nhập lại trên trình duyệt để lấy cookie mới.
   - Trạng thái DB: `apiKeyHealth.primary.status = 'invalid'` hoặc `last_error` chứa `401`.

2. **Lỗi Sentinel / Turnstile Block (Cloudflare Challenge ngầm)**:
   - Log: `ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
   - Cơ chế: Cloudflare / OpenAI Sentinel phát hiện traffic bất thường qua proxy IP, dựng rào cản Turnstile (bắt tick Captcha). Backend headless không thể tick nên request bị từ chối tức thì.
   - Trạng thái DB: `last_error` chứa `Sentinel/Turnstile`.

---

## 2. Vì Sao Pool Có Hàng Trăm Acc Sống Mà Vẫn Sập HTTP 503?

- Trong combo `gpt-web-sol`, danh sách models chứa toàn bộ connections (ví dụ 157 accounts).
- Cấu hình mặc định:
  - `strategy: round-robin`
  - `maxGlobalAttempts: 8`
- **Bẫy Round-Robin dính cụm acc liệt**: Khi con trỏ round-robin xoay tới một dải gồm 8 tài khoản liên tiếp bị 401 hoặc Sentinel block, OmniRoute thử tuần tự 8 lần rồi chạm trần `maxGlobalAttempts = 8`.
- Kết quả: OmniRoute bỏ cuộc và ném thẳng lỗi `HTTP 503: Service Unavailable` ra ngoài, mặc dù trong pool còn hơn 110 accounts hoàn toàn khỏe mạnh.

---

## 3. Quy Trình Cô Lập & Tự Hồi Phục (Self-Healing Playbook)

Script canonical chuẩn: `D:/Taadaa/tools/cooldown_broken_chatgpt.py`

### Bước 1: Cô lập (Cooldown) các Connection Lỗi
Quét database `~/.omniroute/storage.sqlite` và đặt `is_active = 0` cho các account dính 401 hoặc `invalid`:
```sql
UPDATE provider_connections
SET is_active = 0, last_error = '[COOLDOWN] Token expired or invalid auth'
WHERE provider = 'chatgpt-web' AND is_active = 1
  AND (last_error LIKE '%401%' OR json_extract(provider_specific_data, '$.apiKeyHealth.primary.status') = 'invalid');
```

### Bước 2: Thanh Lọc Combo `gpt-web-sol`
Chỉ giữ lại các entry trỏ tới `connectionId` có `is_active = 1` trong SQLite:
```python
clean_models = [m for m in combo_models if active_map.get(m['connectionId']) == 1]
combo['models'] = clean_models
```

### Bước 3: Nâng Cấp Cấu Hình Định Tuyến Kháng Lỗi
Thay đổi tham số combo trong bảng `combos`:
- `strategy`: Chuyển từ `round-robin` sang `cache-optimized` (ưu tiên kết nối đã warm cache và ổn định).
- `config.maxGlobalAttempts`: Tăng từ `8` lên `25`.
- `config.disableSessionStickiness`: Đặt `True` để không bị kẹt dính vào connection vừa phát sinh lỗi.
