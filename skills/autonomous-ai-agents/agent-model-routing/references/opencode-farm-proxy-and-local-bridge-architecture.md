# OpenCode Farm Proxy & Local HTTP Bridge Architecture (2026-09-27)

## Bối cảnh & Vấn đề Cốt lõi
- **Chặn HTTP ngoài (403):** Server OpenCode Zen chặn thẳng cánh các request ngoài với lỗi `HTTP 403: {"type":"FreeTierError","message":"OpenCode's free tier can only be used from within OpenCode"}`.
- **Yêu cầu phiên bản Client:** OpenCode CLI bắt buộc version `>= 1.18.0` (đã nâng cấp lên `1.18.32` qua `npm i -g opencode-ai@latest`).
- **Giới hạn Rate Limit theo IP / Daily Quota:** Gọi dồn dập từ 1 IP dễ dính `429 Too Many Requests` hoặc hết hạn ngạch ngày.
- **Nhu cầu Hermes Fallback / Telegram /model:** Hermes giao tiếp qua HTTP (`/v1/chat/completions`), trong khi OpenCode Free Tier chỉ chạy qua CLI binary `opencode run`.

---

## Kiến trúc Triển khai 2 Tầng

### 1. Tầng Data Plane: Proxy Wrapper (`D:/Taadaa/tools/oc_farm.py`)
- **Pool 69 Proxy Farm:**
  - 35 MikroTik: `mirotik1.taadaa.click:10001..10035` (URL encoded `admin%401:admin%401`).
  - 32 Mobi: `test.taadaa.click:5101..5138` (loại trừ các port gap `5109..5110`, `5119..5120`, `5129..5130`; auth `mobiN:TaadaaMobi#2026!`).
  - 2 Khoalee: `khoalee.duckdns.org:16001..16002`.
- **Cơ chế Lease & Cooldown:**
  - Lưu trạng thái cooldown tại `~/AppData/Local/hermes/oc_farm_cooldown.json` (TTL 300s).
  - Tự động bắt exit code / stderr: khi gặp `429`, `rate limit`, `daily quota`, hoặc lỗi kết nối proxy $\rightarrow$ đưa IP vào cooldown và lập tức xoay sang IP tiếp theo retry (tối đa 3 lần).
- **Môi trường bắt buộc:**
  - `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`.
  - **`NO_PROXY="localhost,127.0.0.1,::1"`** (Bắt buộc để không làm nghẽn tiến trình IPC/TUI nội bộ của OpenCode).

### 2. Tầng Control Plane / Adapter: HTTP Bridge (`D:/Taadaa/tools/opencode_bridge.py`)
- Lắng nghe tại `http://127.0.0.1:20130/v1`.
- **Auto-Sync Model Discovery:**
  - Tự động chạy `opencode models` để nạp danh sách 108 model live.
  - Cache TTL 5 phút; hỗ trợ endpoint ép làm mới tức thì: `GET /v1/models/refresh`.
  - Sinh alias ngắn gọn: `muse-spark-1.3`, `nemotron-3-ultra`, `big-pickle`, `space-bunny`.
- **Xử lý Chat & Streaming:**
  - Hỗ trợ cả `stream: false` và `stream: true` (chuẩn SSE chunks, kết thúc bằng `data: [DONE]`).
  - Chạy nền qua `D:/Taadaa/tools/start_opencode_bridge_hidden.vbs`.

---

## Cấu hình Hermes Integration (`config.yaml`)

```yaml
custom_providers:
  - name: opencode
    base_url: http://127.0.0.1:20130/v1
    api_mode: chat_completions
    api_key: opencode-local-key
    discover_models: true
    model: muse-spark-1.3

fallback_providers:
  - model: muse-spark-1.3
    provider: custom:opencode

model:
  aliases:
    muse: custom:opencode/muse-spark-1.3
    opencode: custom:opencode/muse-spark-1.3
    nemotron: custom:opencode/nemotron-3-ultra
```

### Lệnh dùng trực tiếp trên Telegram:
- `/model muse --session` (hoặc `/model opencode --session`)
- Khi model chính cạn quota, Hermes tự động failover sang `muse-spark-1.3` qua `custom:opencode`.
