# ChatGPT Web Cookie Extraction & OmniRoute Pool Sync

## Mục tiêu
Tự động đăng nhập ChatGPT Web (`https://chatgpt.com`) qua Google SSO trên profile GPMLogin, trích xuất cookie session, validate trên OmniRoute (port 20129), và đồng bộ vào SQLite storage.

---

## 1. Schema & Cấu trúc bảng OmniRoute (`storage.sqlite`)

Đường dẫn DB: `C:\Users\Kibe\.omniroute\storage.sqlite`

### Bảng `provider_connections`
- `id`: UUID của connection.
- `provider`: `'chatgpt-web'`.
- `api_key`: Chuỗi cookie session (khi cập nhật có thể qua API validate hoặc ghi cookie đã mã hóa/thô).
- `is_active`: `1` khi hoạt động.
- `test_status`: `'active'`.
- Các trường reset: `last_error=NULL, last_error_at=NULL, backoff_level=0, rate_limited_until=NULL, updated_at=CURRENT_TIMESTAMP`.

### Bảng `combos` (Lưu ý: Bảng tên là `combos`, KHÔNG phải `provider_combos`)
- `id`: UUID của combo.
- `name`: `'chatgpt-web-pool'`.
- `data`: JSON chứa cấu hình chiến lược và danh sách models:
```json
{
  "name": "chatgpt-web-pool",
  "description": "ChatGPT Web Pool ch\u1ea1y Round-Robin quay v\u00f2ng \u0111\u1ec1u t\u1ea3i",
  "strategy": "round-robin",
  "models": [
    {
      "id": "chatgpt-web-pool-model-<conn_prefix>",
      "kind": "model",
      "model": "chatgpt-web/gpt-5.6-sol-high",
      "providerId": "chatgpt-web",
      "connectionId": "<uuid>",
      "weight": 0,
      "label": "<acc_label>"
    }
  ]
}
```

---

## 2. Quy trình trích xuất & Đồng bộ

1. **Khởi động GPM Profile qua Local API (port 19995):**
   ```http
   GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8
   ```
   Nhận `driver_path`, `remote_debugging_address` (IP:Port).

2. **Kết nối Playwright qua CDP:**
   ```python
   browser = await playwright.chromium.connect_over_cdp(f"http://{remote_debugging_address}")
   context = browser.contexts[0]
   page = context.pages[0] if context.pages else await context.new_page()
   ```

3. **Điều hướng & Vượt rào Cookie Overlay (Bắt buộc):**
   - **BẪY CLICK BLOCKER**: Trang `chatgpt.com` hiện nay có lớp overlay cookie consent (`<div data-octane-static-cookie-consent="">`) chặn đứng toàn bộ tương tác pointer/click của Playwright, gây lỗi `TimeoutError` sau 30s!
   - **Cách xử lý chuẩn qua JS Evaluation**:
     ```python
     # Xóa sạch overlay cookie consent và trigger mở modal login
     page.evaluate("""() => {
         const banner = document.querySelector("[data-octane-static-cookie-consent]");
         if (banner) banner.remove();
         const btn = document.querySelector("button[commandfor='mobile-auth-dialog']");
         if (btn) btn.click();
     }""")
     page.wait_for_timeout(1500)
     
     # Click Continue with Google
     page.evaluate("""() => {
         const btns = Array.from(document.querySelectorAll("button, a"));
         const g = btns.find(b => b.innerText && b.innerText.includes("Google"));
         if (g) g.click();
     }""")
     ```
   - Xử lý Account Chooser (`[data-identifier]`) và nút Tiếp tục (`button:has-text('Tiếp tục')`).
   - Chờ chuyển hướng hoàn tất đến `https://chatgpt.com` (URL không còn chứa `/auth/`).

4. **Trích xuất Cookie Session & Validate:**
   - Lấy toàn bộ cookies từ `context.cookies(["https://chatgpt.com"])`.
   - Gom thành chuỗi cookie: `name=val; name=val; ...`
   - Validate qua OmniRoute API:
     ```bash
     curl -X POST http://127.0.0.1:20129/api/providers/validate \
       -H "Content-Type: application/json" \
       -d '{"provider": "chatgpt-web", "apiKey": "<cookie_str>"}'
     ```
   - Kết quả trả về `{"valid": true}` xác nhận session cookie còn hạn và hoạt động tốt.

5. **Tạo Connection & Gán Proxy 1-1 Bắt Buộc:**
   - Tạo connection mới trên OmniRoute nếu chưa có:
     `POST http://127.0.0.1:20129/api/providers`
     `{"provider": "chatgpt-web", "name": f"{email} (GPM Web)", "apiKey": cookie_str, "isActive": true}`
   - **GÁN PROXY TĨNH 1-1 (CẤM DIRECT)**:
     ```python
     requests.put("http://127.0.0.1:20129/api/settings/proxies/assignments", json={
         "scope": "account",
         "scopeId": created_cid,
         "proxyId": proxy_id
     })
     ```
   - Nạp connection vào combo `chatgpt-web-pool` (`9c68197d-410a-4267-a3e7-c843aa82cab0`).

6. **Dual-Stage Teardown Chống Đơ Lag Máy (Bắt buộc trong finally):**
   - **CẢNH BÁO**: GPM API `profiles/stop/{pid}` KHÔNG diệt process `chrome.exe` trên Windows. Không bao giờ chỉ gọi API stop rồi bỏ qua!
   - Bắt buộc lưu `proc_id = r_start['data'].get('process_id')` lúc mở profile và thực thi dọn dẹp 2 tầng:
     ```python
     finally:
         try: requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
         except Exception: pass
         if proc_id:
             try:
                 pr = psutil.Process(proc_id)
                 for c in pr.children(recursive=True):
                     try: c.kill()
                     except Exception: pass
                 pr.kill()
             except Exception: pass
     ```
