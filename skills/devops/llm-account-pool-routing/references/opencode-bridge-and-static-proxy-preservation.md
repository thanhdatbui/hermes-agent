# OpenCode Bridge & Static Farm Proxy Mapping Runbook

## 1. Kiến trúc Cầu nối OpenCode Bridge (`opencode_bridge.py` :20130)
- **Mục tiêu**: Đưa model free từ OpenCode CLI (`muse-spark-1.3-contributor-free`, `nemotron-3-ultra-free`...) vào làm tầng Fallback cuối cùng cho Hermes Agent và Telegram Gateway.
- **Vấn đề kết nối HTTP Timeout (15s)**:
  - Client `run_agent.py` của Hermes có `connect=15.0s`.
  - OpenCode CLI + proxy farm mất ~18s-20s để khởi động và trả tokens đầu tiên.
  - **Giải pháp**: Cầu nối phải dùng `ThreadingHTTPServer` (đa luồng) và thực hiện **Immediate SSE Flush** (gửi HTTP 200 + chunk `{"role": "assistant"}` trong 0.01s) ngay khi nhận request để Hermes không bị ngắt kết nối `Connection error / ConnectTimeout`.
- **Lọc Model Free**:
  - Không expose toàn bộ 108 model trả phí/lộn xộn của OpenCode.
  - Chỉ lọc 8 model thuộc namespace `opencode/*` (100% free tier): `muse-spark-1.3`, `nemotron-3-ultra`, `nemotron-3.5-lightning`, `mimo-v2.6-flash`, `big-pickle`, `space-bunny`, `ling-3.0-flash-fin`, `longcat-2.5-preview`.

## 2. Nguyên tắc Bảo lưu Proxy Tĩnh (Static Proxy Preservation) khi Cúp điện Farm
- **Bảo lưu Binding Tĩnh**:
  - Toàn bộ tài khoản Google/Antigravity trong OmniRoute (`storage.sqlite`) được gán tĩnh theo `proxy_assignments` (58 acc Mobi `test.taadaa.click:5101..5138`, 5 acc MikroTik `mirotik1.taadaa.click:10001..10035`).
  - Khi dải Mobi cúp điện/rớt mạng:
    * Router **tuyệt đối KHÔNG tự ý tráo đổi proxy** của các tài khoản này sang MikroTik hay IP khác để tránh Google kích hoạt checkpoint / verify danh tính do nhảy IP.
    * Các kết nối gắn Mobi rơi vào trạng thái `SYN_SENT` / timeout và tự động bị đóng băng (cooldown).
    * Nhánh tài khoản gán MikroTik (như `phanlan`, `phungkieu`, `phamthimyduyen`...) và các acc Direct sẽ đứng ra gánh toàn bộ traffic.
  - Khi có điện / mạng phục hồi:
    * Router tự động kích hoạt lại đúng 58 tài khoản trên đúng cổng Mobi ban đầu.
