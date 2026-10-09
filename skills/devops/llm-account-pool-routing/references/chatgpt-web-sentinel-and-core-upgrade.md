# ChatGPT-Web Pool Sentinel (403) Protection & Chromium Core Upgrade Runbook

## 1. Cơ chế phân loại lỗi 403 Sentinel trên OmniRoute
- **Hiện tượng:** Request gọi model ChatGPT-Web (`gpt-5.6-sol-high`, `luna-free`) nhận phản hồi:
  `[403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
- **OmniRoute Router State:**
  OmniRoute tự động đánh dấu connection đó là `testStatus = "banned"` và tắt `isActive = 0`.
- **Rủi ro chí mạng:**
  Nếu không có van chặn `rate_limit_protection = 1`, router hoặc client agentic (Cline/Hermes) có thể tiếp tục thử lại nhiều lần vào endpoint `/conversation`. OpenAI sẽ nhanh chóng leo thang từ **chặn tạm thời (Turnstile/PoW challenge)** sang **vô hiệu hóa/xóa vĩnh viễn tài khoản (Account Deleted / Disabled)**.

## 2. Van bảo vệ bắt buộc: `rate_limit_protection = 1`
- Mọi connection thuộc provider `chatgpt-web` trên OmniRoute **BẮT BUỘC** phải có `rate_limit_protection = 1`:
  ```sql
  UPDATE provider_connections 
  SET rate_limit_protection = 1, updated_at = CURRENT_TIMESTAMP 
  WHERE provider = 'chatgpt-web';
  ```
- **Tác dụng:** Khi tài khoản gặp 403 Sentinel hoặc 429, hệ thống lập tức đưa connection vào trạng thái cooldown cách ly, chặn đứng nguy cơ spam làm chết nick.

## 3. Quy chuẩn nâng cấp Core Chromium trên GPM Profile
- Các tài khoản chạy ChatGPT Web hoặc Google OAuth bắt buộc chạy trên nhân Chromium mới nhất (`142.0.7444.163` - Core 142).
- Nhân Chromium cũ (như Core 127) mang User-Agent cũ, dễ bị Cloudflare Turnstile hạ điểm uy tín (Trust Score) và bắt giải CAPTCHA / Sentinel.
- **Nâng cấp an toàn qua GPM Local API v3:**
  ```python
  import requests
  # Chỉ update cho các profile active (GroupId > 0)
  res = requests.post(
      f"http://127.0.0.1:19995/api/v3/profiles/update/{profile_id}",
      json={"browser_version": "142.0.7444.163"},
      timeout=5
  )
  ```
- Thao tác này an toàn 100%, bảo toàn cookie phiên hiện có và tự động trỏ binary sang `gpm_browser_chromium_core_142\chrome.exe`.
