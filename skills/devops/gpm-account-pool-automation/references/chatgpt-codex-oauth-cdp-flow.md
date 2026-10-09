# ChatGPT Web vs Codex OAuth via GPM CDP — Fast-path, Consent, Onboarding, OmniRoute Sync

Session: 2026-09-13 — batch ChatGPT SSO 33 acc fail 0/33 → root-cause + fix verified trên lamhien/luuhuong.

## 1. Fast-path: acc đã login sẵn ChatGPT
- Sau `page.goto("https://chatgpt.com/auth/login")`, check ngay:
  `if "chatgpt.com" in page.url and "/auth/" not in page.url:` → đã login, SKIP toàn bộ SSO, nhảy thẳng tới bước lấy token.
- Triệu chứng nếu thiếu: timeout 30s chờ nút "Continue with Google" trong khi page đã ở home (vd luuhuong).

## 2. Google Account Chooser — click đúng cách
- Selector đúng: `div[role="link"][data-identifier*="<email>"]`, fallback `div[role="link"][data-identifier*="@gmail.com"]`.
- KHÔNG dùng `locator.click()` — dùng `bounding_box()` + `page.mouse.click(x,y)`.
- Sau click, URL vẫn `.../accountchooser?...` vài giây là bình thường; chờ redirect sang `.../signin/oauth/...`.

## 3. Google Consent (signin/oauth/id) — nút "Tiếp tục" bị chặn click thường
- Playwright `locator('button:has-text("Tiếp tục")')` trả về count=0 dù body text hiện "Tiếp tục".
- Fix: JS evaluate trong DOM:
```python
page.evaluate('''() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const t = btns.find(b => (b.innerText||'').includes('Tiếp tục') || (b.innerText||'').includes('Continue'));
    if (t) t.click();
}''')
```
- Dấu hiệu thành công: title chuyển sang `Loading https://auth.openai.com/api/accounts/callback/google?code=...`.

## 4. Onboarding `auth.openai.com/about-you`
- Điền cả 2 field: `input[name="name"]` (nếu trống → lấy từ profile name hoặc prefix email) + `input[name="age"]` (random 22–28).
- Dùng `click(force=True)` + `keyboard.type(delay=100)` + `Tab` rồi `button[type="submit"]` `click(force=True)`.
- Sau submit chờ redirect `chatgpt.com` (có thể mất 5–10s qua `/api/auth/callback/openai?code=...`).

## 5. Trích token + sync OmniRoute :20129
- chatgpt-web: cookie `__Secure-next-auth.session-token` (có thể chunked `.0`, `.1`...) → `POST /api/providers` với `{provider:'chatgpt-web', name, apiKey, authType:'apikey'}` — **chấp nhận cả 200 và 201**.
- codex: `GET https://chatgpt.com/api/auth/session` → `accessToken` (prefix `ey...`, len>50) → `POST /api/oauth/codex/import-token` với `{accessToken, name}`.
- Verify: `POST /v1/chat/completions` với header `x-connection-id`, model `chatgpt-web/gpt-5.6-luna-free` (web) hoặc `gpt-5.5` (codex).

## 6. Phân biệt Codex vs ChatGPT-Web (đo thực tế 2026-09-13)
- DB OmniRoute: chatgpt-web `authType=apikey` (cookie `eyJhbGci...`); codex `authType=access_token` (OAuth chuẩn).
- Model: codex → `gpt-5.5`, `codex/gpt-5.6-sol*`; web → `chatgpt-web/gpt-5.6-luna*`.
- Test song song `1+1=?`: codex/gpt-5.5 200 OK 19.27s; web/luna-free 200 OK 17.87s — tốc độ tương đương, khác hệ model.
- Ổn định: 3 codex cũ `expired [401] Unauthorized`; 3 chatgpt-web cùng acc vẫn `active` — codex cần refreshToken auto-renew, web phụ thuộc session browser + dễ dính Cloudflare khi mở `chatgpt.com` hàng loạt.
- Kết luận dùng cho user: Codex = dòng code/reasoning chuẩn dev; Web = chat thường. Không thay thế nhau.

## 7. Verify combo `review` có Terra High
```python
requests.get('http://127.0.0.1:20129/api/combos').json()  # tìm combo name='review' → models[0] == codex/gpt-5.6-terra-high
requests.post('http://127.0.0.1:20129/v1/chat/completions', json={'model':'review','messages':[{'role':'user','content':'Say 123'}],'max_tokens':10})
# expect 200, response model == 'gpt-5.6-terra-high'
```

## 8. Pitfalls batch
- Google `challenge/recaptcha` (~15/33) và `challenge/totp` (2FA) khi SSO hàng loạt qua proxy farm → không auto được, phải tách nhóm.
- `chatgpt.com/auth/login` không nút Google = đã login hoặc đã redirect — luôn check URL trước khi click.
