# Bẫy Validate Key Bị Mask Trên OmniRoute & Quy Chuẩn Kiểm Tra Liveness Qua Cổng Nội Bộ

## 1. Bản chất hiện tượng (The Masked Key Trap)
Khi xây dựng script watchdog hoặc cron job tự động kiểm tra sức khỏe và hồi sinh các tài khoản trong pool LLM (ChatGPT-Web, Claude, Codex...) trên OmniRoute (`http://127.0.0.1:20129`):
* Endpoint `GET /api/providers` trả về danh sách các `connections`.
* Vì lý do bảo mật chống rò rỉ credential, OmniRoute che giấu chuỗi API key / session token bằng định dạng mask:
  - Ví dụ: `__Secure****sTow` hoặc `sk-****3isw`.
* Nếu script watchdog lấy trực tiếp giá trị `c.get('apiKey')` bị che này rồi gửi sang endpoint thẩm định:
  - `POST /api/providers/validate` với `{"provider": "chatgpt-web", "apiKey": "__Secure****sTow"}`
  - Upstream OpenAI / provider lập tức từ chối với mã lỗi `HTTP 400 Bad Request` hoặc `invalid_token`.

## 2. Hậu quả vận hành tai hại
1. **False Inactive (Báo động giả):** Tài khoản thực tế token vẫn còn sống nguyên vẹn và đang hoạt động tốt trên upstream, nhưng watchdog lại kết luận nhầm là token đã chết hoặc hết hạn.
2. **Destructive Recovery (Hồi sinh phá hoại):**
   - Do tưởng token đã chết, watchdog tự động kích hoạt luồng cứu hộ mở browser profile GPMLogin qua CDP.
   - Script gọi `context.clear_cookies()` để chuẩn bị login lại từ đầu.
   - Việc xóa sạch cookie làm phá vỡ session thật đang lưu trong trình duyệt.
   - Đối với tài khoản phụ (ví dụ Hotmail không lưu password trong file credentials) hoặc tài khoản dính thử thách Google SSO / 2FA, luồng login tự động thất bại và trả về `EMPTY_SESSION_TOKEN`.
   - Kết quả: Biến một tài khoản đang sống khỏe mạnh thành một tài khoản bị mất session thực sự!

## 3. Quy chuẩn giải pháp kiến trúc (Authoritative Pattern)
Để kiểm tra trạng thái sống/chết của một connection đã tồn tại trên OmniRoute, **CẤM TUYỆT ĐỐI** dùng `/api/providers/validate` với `apiKey` lấy từ danh sách provider.

**BẮT BUỘC** gọi trực tiếp endpoint kiểm thử nội bộ theo ID kết nối:
```http
POST http://127.0.0.1:20129/api/providers/{cid}/test
Content-Type: application/json

{}
```

### Ưu điểm vượt trội:
1. **Giải mã an toàn ở phía Server:** OmniRoute sẽ tự động giải mã ciphertext được lưu trong database SQLite (`storage.sqlite`) bằng khóa mã hóa nội bộ (`enc:v1:...`), lấy ra session token / API key nguyên bản để test trực tiếp với upstream.
2. **Không làm rò rỉ Credential:** Không cần truyền plaintext cookie qua mạng nội bộ.
3. **Phản hồi tức thì $O(1)$ (< 1.000ms):** Trả về structured diagnosis:
   ```json
   {
     "valid": true,
     "error": null,
     "warning": null,
     "refreshed": false,
     "diagnosis": { "type": "ok", "source": "upstream" },
     "latencyMs": 591
   }
   ```
4. **Hồi sinh tức thì không cần mở trình duyệt:** Nếu `res.get("valid") is True`, watchdog chỉ cần cập nhật trạng thái connection trong SQLite:
   ```sql
   UPDATE provider_connections 
   SET is_active=1, test_status='active', last_error=NULL, last_error_at=NULL, backoff_level=0, rate_limited_until=NULL 
   WHERE id=?
   ```
   Tài khoản lập tức quay trở lại pool phục vụ định tuyến trong 0.1s mà không làm gián đoạn người dùng hay tiêu tốn tài nguyên RAM của trình duyệt GPM.
