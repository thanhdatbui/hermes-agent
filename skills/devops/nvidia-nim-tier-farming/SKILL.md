---
name: nvidia-nim-tier-farming
description: "Use when farming NVIDIA NIM free API keys or KiosAPI backup."
version: 1.0.0
author: Hermes Coordinator
tags: [NVIDIA, NIM, Free-Tier, API-Key, GPM, Hotmail, 9Router, KiosAPI, OpenCode]
---

# NVIDIA NIM & Free-Tier LLM Pool Operations

Hướng dẫn tra cứu, khai thác và tự động hóa reg tài khoản bào API key miễn phí từ **NVIDIA NIM (`build.nvidia.com`)** và **KiosAPI (`kiosapi.com`)** làm nguồn dự phòng token cho AI Coding Agents (OpenCode, Claude Code, Cline, Hermes).

---

## 1. Tổng quan & Thông số kỹ thuật

### A. NVIDIA NIM API (`build.nvidia.com`)
- **Cơ chế cấp:** 1.000 credits/tài khoản (Developer Trial). Không cố định hạn sử dụng, không cần thẻ tín dụng.
- **Base URL:** `https://integrate.api.nvidia.com/v1`
- **Header:** `Authorization: Bearer nvapi-...`
- **Endpoint:** `/chat/completions` (chuẩn OpenAI 100%)
- **Top Models phục vụ Coding & Suy luận:**
  - `qwen/qwen2.5-coder-32b-instruct` (Model open-source sinh code và gọi tool tốt nhất)
  - `deepseek-ai/deepseek-r1` (Suy luận thuật toán sâu, fix bug khó)
  - `deepseek-ai/deepseek-v3` (Đa năng, tốc độ cao)
  - `moonshotai/kimi-k3` (Context dài, hỗ trợ tiếng Việt cực mượt)
  - `meta/llama-3.3-70b-instruct`

### B. KiosAPI Hub (`kiosapi.com`)
- **Cơ chế:** Nền tảng New-API v1.0, nhóm `Free` (5 RPM) và `Free-Pro` (30 RPM), tỷ giá 0đ.
- **Điều kiện mở khóa:** Đăng ký email/GitHub + Xác minh liên kết Telegram Bot `@kiosapi_official` (1 lần duy nhất).
- **Base URL:** `https://kiosapi.com/v1`
- **Header:** `Authorization: Bearer sk-...`
- **Top Models Free:** `glm-5.3-free`, `deepseek-v4.1-flash-free`, `kimi-k3-free`, `grok-4.7-free`, `qwen3.8-flash-free`.

---

## 2. Quy trình Tự động hóa Reg NVIDIA NIM qua GPM + Hotmail

Dàn máy có sẵn profile GPM và Hotmail (tại `D:/Taadaa/Hotmail` hoặc kho `taikhoan_dat_v2_updated .xlsx`).

### Các bước trong luồng (Playwright CDP):
1. **Khởi chạy GPM Profile:**
   - Gọi GPM local API: `POST http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
   - Lấy `remote_debugging_address` (ví dụ `127.0.0.1:62719`).
2. **Điều hướng:**
   - Mở `https://build.nvidia.com/explore/discover?modal=signin`.
   - Điền Email Hotmail -> Bấm Enter hoặc chọn *Log In With Microsoft*.
3. **Microsoft OAuth:**
   - Tự động điền mật khẩu chuẩn của Hotmail (`passwd`).
   - Bấm Đăng nhập -> Tự động redirect về `login.nvgs.nvidia.com/v1/create-account`.
4. **Vượt hCaptcha & Tạo Key:**
   - Form hiện hCaptcha dạng Puzzle kéo thả (`Drag the letter / shape into empty cell`).
   - Sau khi pass captcha -> Submit `Create Account`.
   - Vào trang model (ví dụ `https://build.nvidia.com/moonshotai/kimi-k3`), bấm `Generate API Key` -> Sao chép chuỗi `nvapi-...`.

---

## 3. Dịch vụ Giải hCaptcha Tự động (Khi chạy Batch)

| Nhà cung cấp | Loại Task hCaptcha | Chi phí / 1.000 captcha | Thời gian giải |
| :--- | :--- | :--- | :--- |
| **YesCaptcha** (`yescaptcha.com`) | AI Classification / Token | 2.0 – 5.0 RMB (~7k – 18k VNĐ) | 1 – 3s |
| **CapSolver** (`capsolver.com`) | `HCaptchaTurbo` / `ProxyLess` | $0.60 – $0.80 (~15k – 20k VNĐ) | 1 – 5s |
| **2Captcha** (`2captcha.com`) | Token / Image click | $2.99 (~75k VNĐ) | 10 – 20s |

> **Chi phí thực tế:** Giải 100 acc chỉ tốn ~1.500đ – 2.000đ VNĐ nhưng thu về 100.000 API credits của NVIDIA.

---

## 4. Tích hợp vào Hạ tầng Proxy Farm & OpenCode

### A. Nạp vào 9Router (`localhost:20128`) hoặc Omni (`localhost:20129`)
- **Tạo Custom Channel:**
  - Type: `OpenAI`
  - Base URL: `https://integrate.api.nvidia.com/v1`
  - API Keys: Dán danh sách các key `nvapi-...` (mỗi dòng 1 key để 9Router tự động xoay vòng và fallback khi hết 1.000 credits).
- **Mô hình chịu tải:**
  1. Primary: Gemini Flash/Pro (qua Google AI Studio / OAuth pool).
  2. Fallback 1: NVIDIA NIM Pool (`qwen2.5-coder-32b`, `deepseek-r1`).
  3. Fallback 2: KiosAPI Free Group (`sk-...`).

### B. Cấu hình OpenCode CLI
Trong file cấu hình OpenCode (`opencode.json`):
```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": "custom",
  "baseURL": "http://localhost:20128/v1",
  "apiKey": "9router-internal-key",
  "model": "qwen/qwen2.5-coder-32b-instruct"
}
```

---

## 5. Cạm bẫy & Lưu ý (Pitfalls)

1. **Không reg ngâm hàng loạt trước:** NVIDIA trial credits không cố định ngày hết hạn, nhưng có thể bị quét stale account hoặc đổi policy (bắt verify thẻ). Chỉ nên reg theo nhu cầu (On-Demand) từng đợt 10–20 key khi Gemini cạn quota hoặc cần model chuyên sâu.
2. **hCaptcha Puzzle:** Không dùng click chuột tọa độ mù; bắt buộc giải bằng mắt người dùng hoặc nạp API CapSolver/YesCaptcha với task `HCaptchaClassification`.
3. **An toàn bảo mật mã nguồn:** NVIDIA NIM là enterprise endpoint của NVIDIA nên an toàn. Ngược lại, **KiosAPI là server proxy trung gian** — TUYỆT ĐỐI KHÔNG ném private repo, API key hay credential nhạy cảm qua KiosAPI.
