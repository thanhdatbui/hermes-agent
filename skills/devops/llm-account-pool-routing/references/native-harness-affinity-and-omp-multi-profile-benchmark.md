# Native Harness Affinity, Multi-Profile OMP Integration, and Benchmark Invariants

## 1. Bất biến Đối Soát & Benchmark Giữa Các Harness (Benchmark Parity Invariants)

Khi tổ chức giải đấu hoặc benchmark đối soát giữa 2 runner/harness khác nhau (ví dụ: `ag_cli.py` Antigravity Go Native vs `omp_cli.py` TypeScript/Bun):

1. **Đồng nhất Model & Thinking Effort (Bắt buộc 100%):**
   - Không được phép so sánh khập khiễng khi một bên chạy `thinking: medium` còn một bên chạy `thinking: default / auto / minimal`.
   - `ag_cli.py` mặc định dùng `gemini-3.8-flash-medium` (hậu tố `-medium` ép backend Cloud Code Assist chạy Thinking Effort Medium).
   - `omp_cli.py` khi gọi `google-antigravity/gemini-3.8-flash` BẮT BUỘC phải truyền cờ `--thinking medium`. Thiếu cờ này, model chạy minimal thinking, code sinh ra cộc lốc, thiếu docstring, gộp assert bằng `and` và nhận điểm đánh giá thấp hơn.
2. **Bất biến Profile Cooldown (Cùng Account = Cùng Quota):**
   - Tuyệt đối KHÔNG failover giữa 2 harness trên CÙNG MỘT PROFILE khi gặp lỗi `429 Too Many Requests`.
   - Cả AGY và OMP trên cùng một profile đều xác thực qua cùng một tài khoản Google Cloud và cùng chung 1 IP proxy. Khi tài khoản chạm trần quota, cả 2 harness đều sẽ bị chặn 429 như nhau.
   - **Quy tắc xoay tua chuẩn:** Khi gặp 429 hoặc cooldown, bắt buộc xoay tua sang profile khác (`acc_02` ➔ `acc_03`), cấm chuyển đổi runner trên cùng profile.

## 2. Nguyên Lý "Native Harness Affinity" (Harness Chính Chủ vs Universal Agent)

"Model nào thì nên gắn với harness của chính nhà sản xuất tạo ra nó":

| Tiêu chí | **AGY CLI (`ag_cli.py`)** | **OMP CLI (`omp_cli.py`)** |
| :--- | :--- | :--- |
| **Nhà phát triển** | Google (Antigravity IDE Team) | Cộng đồng mã nguồn mở (Oh My Pi / Pi Agent) |
| **Ngôn ngữ & Runtime** | Go Compile Native (Mã máy x86_64) | Bun / TypeScript / Node.js runtime |
| **Số lượt bắt tay qua Proxy (Round-trips)** | **1 lượt duy nhất:** Kết nối thẳng socket TLS và stream token | **3 - 4 lượt tuần tự:** Token refresh ➔ `loadCodeAssist` ➔ `onboardUser` ➔ chat completion |
| **Độ trễ trung bình trên Proxy 4G** | **~30s/task** (Rất ổn định, dao động 28-34s) | **~60s - 120s/task** (Dễ bị nghẽn do nhiều RTT qua sóng di động) |
| **Chất lượng mã nguồn sinh ra** | Đầy đủ docstring, comment quy chuẩn, 10+ assert test cases có message chi tiết | Tinh gọn, type hint đầy đủ, nhưng thiếu docstring và assert trần trụi |
| **Vai trò phân bổ tối ưu** | **Runner số 1 cho mọi tác vụ code Gemini** | **Universal Sandbox / Runner dự phòng** khi cần gọi các model ngoài hệ sinh thái (DeepSeek, Grok, Qwen, Ollama) |

## 3. Kiến Trúc Native Google Antigravity OAuth Trong OMP

OMP hỗ trợ kết nối trực tiếp lên Google Antigravity qua OAuth Client chính thức của OMP mà không cần qua proxy trung gian local (`omniroute`):

### A. Thông số OAuth Client OMP:
- **Client ID:** `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`
- **Client Secret:** `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`
- **Endpoint Token:** `https://oauth2.googleapis.com/token`
- **Endpoint API:** `https://daily-cloudcode-pa.googleapis.com`

### B. Cấu trúc lưu trữ SQLite `agent.db`:
OMP lưu credentials trong bảng `auth_credentials` tại đường dẫn sandbox riêng:
- `C:/Users/Kibe/.omp/profiles/<name>/agent/agent.db`
- `C:/Users/Kibe/.omp/profiles/<name>/.omp/agent/agent.db`

Schema bản ghi:
```sql
INSERT INTO auth_credentials (
    provider, credential_type, data, disabled_cause, identity_key, created_at, updated_at
) VALUES (
    'google-antigravity',
    'oauth',
    '{"refresh": "...", "access": "...", "expires": 1792557000000, "email": "...", "projectId": "default-gemini-project", "authorizedAt": 1792553000000}',
    NULL,
    'email:...@gmail.com',
    strftime('%s', 'now'),
    strftime('%s', 'now')
);
```

### C. Quy trình cấp mới Access Token qua Proxy Profile:
1. Đọc `refresh_token` từ `D:/Taadaa/agy_profiles/<name>/.gemini/oauth_creds.json`.
2. Gửi request POST `grant_type=refresh_token` qua proxy di động tương ứng của profile đó lên Google OAuth token endpoint.
3. Tính toán `expires = now_ms + (expires_in * 1000)` và ghi payload JSON vào `agent.db`.
4. Cô lập môi trường khi khởi chạy:
   - `USERPROFILE` và `HOME` trỏ về `C:\Users\Kibe\.omp\profiles\<name>` (tránh link chùm `~/.omp/install-id`).
   - `HTTP_PROXY` và `HTTPS_PROXY` trỏ đúng proxy profile (che credentials `***:***` khi in log).
   - Truyền đầy đủ `--model google-antigravity/gemini-3.8-flash --thinking medium`.
