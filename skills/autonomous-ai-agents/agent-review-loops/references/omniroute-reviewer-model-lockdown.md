# OmniRoute Reviewer Model Lockdown & Anti-Drift Guard

## 1. Bối cảnh sự cố (Root Cause)
Khi reviewer được cấu hình qua combo `review` trên OmniRoute (:20129) chạy pool tài khoản ChatGPT Web:
- **Hiện tượng:** Agent/Subagent tự ý probe danh sách model hoặc tự suy diễn rằng bản "Pro" sẽ audit kỹ hơn, nên tự gõ cờ CLI:
  `--model "chatgpt-web/gpt-5.6-sol-pro"`
- **Hậu quả 1:** Dòng `gpt-5.6-sol-pro` trên Web Plus có quota cực ngặt (chỉ vài request/3-5h). Gọi trực tiếp sẽ dính ngay lỗi:
  `[502]: You've hit your limit. Please try again later.`
- **Hậu quả 2 (Chữa cháy sai lầm):** Khi dính lỗi 502, Agent tự ý hạ cấp sang `--model "chatgpt-web/gpt-5.6-sol-instant"`. Bản Instant không có thinking tokens (0 reasoning), làm rỗng hoàn toàn chất lượng kiểm định.

## 2. Quy chuẩn bắt buộc (Invariants)
- Model reviewer mặc định và chuẩn mực duy nhất là **`review`** (hoặc đích danh **`chatgpt-web/gpt-5.6-sol-high`**).
- Tuyệt đối **CẤM** truyền các chuỗi model: `sol-pro`, `sol-instant`, `pro`, `instant`.
- Khi gặp lỗi 502 hoặc quota limit: **CHỈ** được phép retry cùng model sau backoff hoặc báo cáo Coordinator, **CẤM TUYỆT ĐỐI** tự ý đổi sang model khác để chữa cháy.

## 3. Kiến trúc phòng thủ đa tầng (Defense-in-Depth)

### Tầng 1: CLI Validation (`closeout_gate.py`)
- Khai báo whitelist tường minh:
  ```python
  ALLOWED_REVIEW_MODELS = {"review", "chatgpt-web/gpt-5.6-sol-high"}
  FORBIDDEN_MODEL_PATTERNS = ["sol-pro", "sol-instant", "gpt-5.6-sol-pro", "gpt-5.6-sol-instant"]
  ```
- Kiểm tra ngay sau `args = parser.parse_args()`:
  Nếu vi phạm, ghi log telemetry `MODEL_DRIFT_BLOCKED` ra `stderr` và lập tức `sys.exit(2)`.

### Tầng 2: Pre-tool Shell Hook (`D:/Taadaa/tools/hooks/guard_model_drift.py`)
- Hook bắt mọi lệnh `terminal` trước khi chạy.
- Nếu lệnh chứa `closeout_gate` và có cờ `--model` chứa `sol-pro`/`sol-instant`/`pro`/`instant`:
  Trả về `{"action": "block", "message": "..."}` để ngắt lệnh ngay tại cửa ngõ Hermes.

### Tầng 3: OmniRoute Combo Routing (:20129)
- Combo `review` đã cấu hình Tier 0 là `chatgpt-web-pool` (16 accounts Web Plus) chạy Round-Robin quay vòng đều tải với model `chatgpt-web/gpt-5.6-sol-high`.
- Request gửi tới endpoint `/v1/chat/completions` với `model: "review"` được đảm bảo chia đều tải và bảo toàn quota Claude Opus CLI.
