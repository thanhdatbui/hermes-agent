# NVIDIA NIM & New-API Free Tier Ingestion & Account Pool Integration

## Bối cảnh
Khi chạy Agentic Coding (OpenCode, Claude Code, Cline, Hermes), token context phình rất nhanh (50k - 200k tokens/turn). Các gói thuê bao cố định ($10 Go) dễ cạn quota trong 1-2 ngày. Dưới đây là kiến trúc tích hợp các nguồn "tier free" (NVIDIA NIM Catalog, KiosAPI / New-API) vào hạ tầng 9Router (:20128) / OmniRoute (:20129) và Account Pool.

---

## 1. NVIDIA NIM Catalog (build.nvidia.com)

### Đặc điểm kỹ thuật
- **Endpoint:** `https://integrate.api.nvidia.com/v1` (Chuẩn OpenAI `/chat/completions`)
- **Format API Key:** `nvapi-...`
- **Quota:** 1.000 credits khởi tạo cho mỗi account mới (đăng ký qua Email/Hotmail/Gmail không cần thẻ tín dụng).
- **Các Model Code / Agentic hàng đầu:**
  - `qwen/qwen2.5-coder-32b-instruct` (Tối ưu nhất cho agentic tool-calling & code refactor)
  - `deepseek-ai/deepseek-r1` (Suy luận thuật toán, logic phức tạp)
  - `deepseek-ai/deepseek-v3` (Code tổng quát, sinh test)
  - `meta/llama-3.3-70b-instruct` (Đa năng, context dài)

### Tích hợp vào 9Router / OmniRoute
- Tạo Provider `Custom OpenAI` hoặc `NVIDIA NIM`.
- Base URL: `https://integrate.api.nvidia.com/v1`
- Nạp danh sách API keys `nvapi-...` từ farm accounts vào Key Pool để kích hoạt Round-Robin / Automatic Failover khi gặp 402/429.

---

## 2. KiosAPI / New-API Hubs (kiosapi.com)

### Đặc điểm kỹ thuật
- **Platform:** New-API v1.x
- **Endpoint:** `https://kiosapi.com/v1`
- **Cơ chế Free Group:**
  - Nhóm `Free`: 5 RPM, tỷ giá 0đ
  - Nhóm `Free-Pro`: 30 RPM, tỷ giá 0đ
  - **Yêu cầu mở khóa:** Hoàn thành xác thực Telegram Bot + gia nhập channel chính thức.
- **Model Free nổi bật:**
  - `deepseek-v4.1-flash-free` / `deepseek-v4-flash-free`
  - `glm-5.3-free` / `glm-5.3-flash-free`
  - `kimi-k3-free`
  - `grok-4.7-free`
  - `qwen3.8-flash-free` / `qwen3.8-27b-free`

---

## 3. Override cấu hình OpenCode Client
Khi sử dụng OpenCode CLI trỏ qua Proxy nội bộ hoặc trực tiếp:

```json
{
  "provider": "custom",
  "baseURL": "http://127.0.0.1:20128/v1",
  "apiKey": "local-router-key",
  "model": "qwen/qwen2.5-coder-32b-instruct"
}
```
Hoặc qua biến môi trường:
```bash
export OPENCODE_BASE_URL="http://127.0.0.1:20128/v1"
export OPENCODE_API_KEY="local-router-key"
```
