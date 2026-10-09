# ChatGPT-Web Sentinel 403 vs Codex Developer OAuth & Pool Timeout (45s vs 90s)

## 1. Bản chất kỹ thuật: ChatGPT-Web vs Codex OAuth (Cùng 1 tài khoản)

### A. Sự thật về nhãn "banned" trên ChatGPT-Web
- **Hiện tượng**: Trên OmniRoute (`:20129`), tài khoản `chatgpt-web` bị tắt công tắc (`is_active = 0`) với nhãn `test_status = 'banned'` kèm lỗi:
  `[403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
- **Bản chất**: **TÀI KHOẢN KHÔNG BỊ BAN!** Đây là lỗi đặt tên trạng thái của dev OmniRoute: cứ nhận HTTP 403 là gán biến `banned`.
- Giao diện web `chatgpt.com` (`/backend-api/conversation`) được bảo vệ bởi **Cloudflare Turnstile & Sentinel** (Bot Detection). Khi gửi request HTTP giả lập, Cloudflare nghi ngờ bot và chặn lại bắt giải Captcha.
- **Ban thật vs Bị Challenge**:
  - *Ban thật*: Trình duyệt báo *"Your account has been deactivated"*. Cả Web lẫn Codex đều chết 100%, token bị thu hồi.
  - *Bị Challenge (Sentinel 403)*: Tài khoản sống 100%, chỉ cần mở profile GPM thật qua IP 4G để refresh cookie là hồi sinh ngay.

### B. Tại sao cùng tài khoản đó bên Codex CLI chạy mượt 100%?
- Codex CLI chạy qua giao thức **OAuth PKCE chính thức của OpenAI** (`/v1/responses` hoặc `/backend-api/lat/r`).
- Backend dành cho developer/terminal tuyệt đối **KHÔNG có Cloudflare Turnstile hay Sentinel** (vì terminal không thể giải Captcha).
- Do đó, tài khoản dính cờ Sentinel bên Web vẫn phục vụ mượt mà trên pool Codex mà không dính bất kỳ lỗi nào.

---

## 2. Quy trình Hồi sinh ChatGPT-Web tự động qua GPM + Playwright CDP

### 3 Lỗi phổ biến của script hồi sinh cũ:
1. **Lấy nhầm cookie thô**: Lấy toàn bộ cookie gộp `k1=v1; k2=v2` -> OmniRoute từ chối, báo lỗi `[401]: ChatGPT auth failed`.
   - *Cách chuẩn*: Chỉ trích xuất cookie `__Secure-next-auth.session-token` (ghép đầy đủ các chunk `.0`, `.1` nếu có). Token hợp lệ bắt đầu bằng `eyJhbG...` và có độ dài > 50 ký tự.
2. **Kẹt màn hình "Phiên của bạn đã kết thúc"**: Cần click `[Đăng nhập]`, chọn `Continue with Google`, chọn tài khoản và click `[Tiếp tục]` trên trang Google Consent (`/oauth/id`).
3. **Kẹt form Onboarding OpenAI**: Trang `about-you` yêu cầu điền tuổi trực tiếp `input[name="age"]`. Nếu không điền, trang treo 60s và văng phiên. Luôn điền `input[name="age"] = 24`.

### Code trích xuất token chuẩn (Python Playwright):
```python
def extract_clean_session_token(context):
    cookies = context.cookies(["https://chatgpt.com"])
    token = None
    chunks = {}
    for c in cookies:
        cn, cv = c.get("name", ""), c.get("value", "")
        if cn == "__Secure-next-auth.session-token":
            token = cv
            break
        elif cn.startswith("__Secure-next-auth.session-token."):
            chunks[cn.split(".")[-1]] = cv
    if not token and chunks:
        sorted_keys = sorted(chunks.keys(), key=lambda x: int(x) if x.isdigit() else x)
        token = "".join(chunks[k] for k in sorted_keys)
    return token
```

---

## 3. Bẫy Timeout 45s (HTTP 499) vs 90s trên OmniRoute Combo

### Hiện tượng:
- Request gửi vào pool Luna liên tục nhận mã **HTTP 499** (Client Closed Request) ở đúng các mốc thời gian: `45021 ms`, `45790 ms`, `46346 ms`, `46580 ms`, `47022 ms`.

### Nguyên nhân:
- Combo `codex-luna-pool` có cấu hình `targetTimeoutMs: 45000` (45 giây).
- Model reasoning sâu (như `gpt-5.6-luna-high` hoặc các bài toán phức tạp) cần 40–80 giây suy luận ngầm. Khi vượt quá 45 giây, OmniRoute ngắt kết nối upstream và trả về 499.
- Tồn tại song song 2 combo: `codex-luna-pool` (45s cũ) và `codex-luna` (90s mới). Tuy nhiên, combo cha `omni-worker` (Tier 3) vẫn trỏ vào `codex-luna-pool`, khiến mọi request đổ vào worker đều dính bẫy 45s!

### Quy tắc chuẩn hóa:
1. **Luôn đặt `targetTimeoutMs >= 90000` (90 giây)** cho mọi combo chạy model có reasoning (Luna High, Terra High, Sol High).
2. **Loại bỏ phân mảnh combo**:
   - Không duy trì 2 combo alias (`*-pool` và `*`).
   - Hợp nhất về 1 combo duy nhất chuẩn: `codex-luna`, `codex-terra`.
   - Cập nhật tất cả `combo-ref` bên trong combo cha (`omni-worker`).
   - Xóa bỏ hoàn toàn combo thừa khỏi bảng `combos` trong `storage.sqlite`.

---

## 4. Kỷ luật Concurrency khi chạy Healer Watchdog (User Directive)

- **User Directive**: Với host Kibe (32–64GB RAM), chạy **5 workers song song** (`ThreadPoolExecutor(max_workers=5)`), không chạy tuần tự 1-by-1 gây chậm trễ.
- **Lịch chạy**: Giữ nguyên **05:00 AM sáng hàng ngày** (`0 5 * * *`) trong cron `chatgpt-web-pool-healer-watchdog`. Khung giờ này vắng tải, tránh xung đột và sẵn sàng cho ca làm việc ban ngày.
- **Teardown**: Mỗi worker khi xong bắt buộc gọi `stop_profile` qua GPM API và dọn dẹp các tiến trình Chrome mồ côi trong khối `finally`.
