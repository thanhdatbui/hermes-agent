# OmniRoute Combo Routing & Proxy Isolation Operational Runbook

## 1. Bản chất sự cố & Cạm bẫy chẩn đoán
1. **Lầm tưởng UI Quota vs Lượng tải thực tế:**
   - Các card Dashboard của OmniRoute chỉ thống kê các model nặng (Opus, Sonnet, Gemini 3.1 Pro High).
   - Traffic nền và các agent subagent chủ yếu bắn vào `gemini-3.8-flash-tiered`. Model này **không hiển thị thanh quota trên card Dashboard**, dẫn đến việc nhìn Dashboard thấy 100% full nhưng acc thực tế vẫn nhận traffic hoặc bị kẹt hàng đợi mà không biết. Luôn phải truy xuất `/api/usage/history` để lấy `byAccount` thực tế.
2. **Cơ chế Fallback Proxy Deterministic khi mất điện / rớt mạng:**
   - Trong `src/lib/db/settings.ts`, khi proxy tĩnh của account bị unreachable (`!isProxyReachable`), OmniRoute kích hoạt `resolveProviderPoolFallbackProxy`.
   - Thuật toán dùng `hashConnectionId(connectionId) % reachable.length`. Đây là hàm băm xác định: nếu danh sách proxy sống cố định (ví dụ MikroTik 10001..10035), mỗi account sẽ luôn gắn chặt vào ĐÚNG 1 port proxy sống duy nhất, không bị nhảy lung tung gây checkpoint.
3. **Cạm bẫy Headroom vs Least-Used trên Pool lớn (>15 accs qua proxy):**
   - Strategy `headroom` trước mỗi request sẽ quét `mapWithConcurrency(targets, 5)` gọi trực tiếp sang upstream Google để lấy % saturation (5h/weekly).
   - Trên pool 20 accs chạy qua mạng proxy có độ trễ, việc thăm dò này tạo ra bão 40 request HTTP, đẩy latency lên >30s -> gây lỗi 499 (Client Closed Request) và semaphore timeout.
   - **Giải pháp chuẩn:** Dùng `least-used` (đo trực tiếp trên RAM `metrics.byTarget`, zero latency) kết hợp `sessionStickiness` và `stickyRoundRobinLimit`.

## 2. Tiêu chuẩn cấu hình Combo Pool theo từng nhóm
| Nhóm Pool | Combo điển hình | Strategy | Sticky Limit | Queue Timeout | Mục đích |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pro Gemini** | `ag-gemini-pool-3`, `ag-gemini-pool-3-37` | `least-used` | **15** | 3000ms | Ưu tiên cày acc rảnh quota, giữ prompt cache suốt 15 calls budget subagent, failover nhanh khi nghẽn mạng |
| **Codex / Claude AG** | `codex-terra`, `codex-luna`, `ag-opus`, `ag-sonnet`, `ag-gemini-free-pool` | `least-used` | **15** | 2000ms | Chia đều hạn mức free, giữ prompt cache nguyên task, tránh bẫy `cache-optimized` tắt nhầm stickiness |
| **ChatGPT-Web** | `chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna` | `p2c` | **0** (disable stickiness) | 1000ms | Tản đều ngẫu nhiên theo latency & success rate, bảo vệ session web tránh bị Cloudflare / OpenAI ban |

## 3. Khôi phục tự động (Auto-Healer) & Nạp tự động vào Pool Free
1. **Lỗi Antigravity bị tắt nhầm (`isActive: 0` nhưng `testStatus: active`):**
   - Nguyên nhân thường do nạp OAuth bị thiếu `project_id = null`, khiến hệ thống tưởng thiếu GCP project và cách ly.
   - Watchdog hàng giờ (`cron_omni_activate_soaked_codex.py`) phải tự động bù `project_id = 'aicode-consumers'` và bật lại `is_active = 1` cho các acc `test_status = 'active'`.
2. **Khép kín vòng đời OAuth GPM -> Pool Free:**
   - Script nạp OAuth (`cron_gpm_oauth_full_pool.py`) sau khi exchange token thành công bắt buộc phải gọi API `PUT /api/combos` để nạp ngay ID connection vào `ag-gemini-free-pool` và `ag-gemini-free-pool-37`. Không để tình trạng acc có trong `api/providers` nhưng combo không có target.
