# OpenCode Free Tier Farm Proxy Integration & Hermes Fallback Bridge

## 1. Bản chất Kỹ thuật & Rào cản Upstream (2026-09)
- **OpenCode Free Models:** `muse-spark-1.3-contributor-free`, `nemotron-3-ultra-free`, `space-bunny-free`, `big-pickle`, `ling-3.0-flash-fin-free`.
- **Rào cản HTTP 403:** Upstream OpenCode Zen chặn toàn bộ request HTTP trực tiếp từ proxy ngoài (`HTTP 403: OpenCode's free tier can only be used from within OpenCode`).
- **Yêu cầu Binary CLI:** Bắt buộc phải chạy qua binary OpenCode CLI phiên bản `>= 1.18.0` (máy hiện tại: `1.18.32`).
- **Giới hạn Rate-limit / Daily Quota:** Giới hạn theo IP nguồn.

## 2. Giải pháp Điều phối: `oc_farm.py` (Pool 69 Proxy Farm)
- Vị trí: `D:/Taadaa/tools/oc_farm.py`.
- Tự động xoay vòng Round-Robin & Cooldown qua 69 proxy có sẵn của farm:
  - 35 MikroTik (`mirotik1.taadaa.click:10001..10035`, auth `admin%401:admin%401`).
  - 32 Mobi (`test.taadaa.click:5101..5138`, trừ các port gap).
  - 2 Khoalee (`khoalee.duckdns.org:16001..16002`).
- **Bất biến Môi trường:** BẮT BUỘC inject `NO_PROXY="localhost,127.0.0.1,::1"` cùng `HTTPS_PROXY` để không làm nghẽn tiến trình IPC/TUI của OpenCode.
- **Tự động Retry:** Bắt mã `429`, `rate limit`, `daily quota`, hoặc rớt mạng $\to$ đưa proxy vào cooldown (`~/AppData/Local/hermes/oc_farm_cooldown.json`) và tự đổi IP retry tối đa 3 lần.

## 3. Cầu nối Hermes Telegram Fallback: `opencode_bridge.py`
- Vị trí: `D:/Taadaa/tools/opencode_bridge.py`.
- Khởi động ngầm: `D:/Taadaa/tools/start_opencode_bridge_hidden.vbs` (chạy trên port `http://127.0.0.1:20130/v1`).
- Đóng vai trò là một OpenAI-compatible API adapter cục bộ, chuyển request `/v1/chat/completions` thành lệnh gọi subprocess `oc_farm.py run --format json` và stream kết quả về Hermes.

## 4. Cấu hình Hermes (`~/.hermes/config.yaml`):
```yaml
custom_providers:
  - name: opencode
    base_url: http://127.0.0.1:20130/v1
    api_mode: chat_completions
    api_key: opencode-local-key
    model: muse-spark-1.3
    models:
      muse-spark-1.3: {context_length: 128000}
      nemotron-3-ultra: {context_length: 128000}

fallback_providers:
  - model: gpt-5.6-luna
    provider: custom:9router
  - model: muse-spark-1.3
    provider: custom:opencode

model:
  aliases:
    muse: custom:opencode/muse-spark-1.3
    opencode: custom:opencode/muse-spark-1.3
    nemotron: custom:opencode/nemotron-3-ultra
```

## 5. Sử dụng trên Telegram:
- Khi model chính hết sạch quota (429): Hermes tự động trượt fallback tầng cuối về `muse-spark-1.3` qua `oc_farm.py`.
- Gõ trực tiếp trên Telegram: `/model muse --session` hoặc `/model opencode --session`.
