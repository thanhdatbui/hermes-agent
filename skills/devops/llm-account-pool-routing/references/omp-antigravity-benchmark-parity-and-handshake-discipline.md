# OMP & Antigravity Benchmark Parity and Handshake Discipline

## 1. Nguyên Tắc Cốt Lõi Khi Benchmark Harness (Parity Rule)
- **Đồng nhất Model & Thinking Effort (Bắt buộc)**:
  * Khi đối soát benchmark giữa các runner khác nhau (ví dụ: `ag_cli.py` vs `omp_cli.py`), không chỉ cùng tên model cơ sở mà bắt buộc phải cùng cấu hình suy nghĩ (`thinking effort` / `reasoning level`).
  * `ag_cli.py` mặc định dùng `gemini-3.8-flash-medium` ép `Thinking Effort: Medium`.
  * `omp_cli.py` khi gọi `google-antigravity/gemini-3.8-flash` BẮT BUỘC phải truyền cờ `--thinking medium`. Nếu thiếu cờ này, OMP sẽ rơi về default `auto/minimal`, khiến model suy nghĩ sơ sài, sinh code cộc lốc, test suite thiếu chẩn đoán và làm sai lệch hoàn toàn kết quả đối soát.

## 2. Handshake Latency & Network Round-Trips trên Proxy Di Động (4G)
- **Cơ chế Handshake Proxy**:
  * Mỗi kết nối HTTPS qua HTTP proxy bắt buộc qua 3 pha bắt tay tuần tự: TCP Handshake (1 RTT) -> HTTP CONNECT Tunnel Handshake (1 RTT) -> TLS Handshake (1-2 RTT).
  * Trên proxy 4G di động (độ trễ cao 150-300ms, dễ jitter):
    - `agy.exe` (Go Native): Chỉ mở 1 kết nối duy nhất từ token đã lưu, stream trực tiếp, latency ổn định ~25-35s.
    - `omp` (Bun/TypeScript): Mở từ 3-4 round-trips mạng (token refresh -> loadCodeAssist/account check -> completion request). Việc bắt tay liên tiếp 3-4 lần khiến latency đội lên 80-200s và dễ bị Google Cloud đánh dấu burst traffic dẫn đến HTTP 429 Too Many Requests.
- **Nguyên tắc "Model nào đi với Harness chính chủ đó"**:
  - Gemini: Ưu tiên tối cao `ag_cli.py` (Antigravity CLI chính chủ Go native).
  - Claude: Ưu tiên tối cao `claude_worker.py` (Claude Code CLI chính chủ Anthropic).
  - OMP CLI: Đóng vai trò Universal Sandbox / Fallback Runner khi cần tích hợp model ngoài (DeepSeek, Grok, Qwen, Ollama local) hoặc làm harness dự phòng độc lập.

## 3. Quy Tắc Xoay Tua Profile (Anti-Co-Account Fallback)
- **Tuyệt đối cấm fallback OMP trên cùng profile/account**:
  * `ag_cli.py` và `omp_cli.py` của cùng một profile (ví dụ `acc_02`) dùng chung 1 email Google và 1 hạn ngạch quota trên Google Cloud.
  * Nếu một profile bị rate limit 429 / cooldown trên AGY, việc chuyển sang gọi OMP trên CHÍNH PROFILE ĐÓ là hoàn toàn vô nghĩa và chắc chắn fail.
  * Khi gặp lỗi 429 hoặc cooldown: BẮT BUỘC PHẢI XOAY TUA SANG PROFILE KHÁC (`acc_02` -> `acc_03`), không đổi harness trên cùng một account.

## 4. Cơ Chế Mapping Multi-Profile OAuth cho OMP
- OMP lưu credentials trong SQLite `C:/Users/Kibe/.omp/profiles/<name>/agent/agent.db` (và `.omp/agent/agent.db`) tại bảng `auth_credentials`.
- Refresh token từ `agy_profiles/<name>/.gemini/oauth_creds.json` có thể dùng để xin access token mới cho OMP thông qua Client ID của OMP (`1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`).
- Payload `auth_credentials` cho provider `google-antigravity`:
  * `provider`: `"google-antigravity"`
  * `credential_type`: `"oauth"`
  * `data`: JSON chứa `refresh`, `access`, `expires`, `email`, `projectId: "default-gemini-project"`, `authorizedAt`.
