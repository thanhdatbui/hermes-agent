# Batch Aggregator & Scoped Grep Discipline

## 1. Batch Aggregator: Session Lost vs Temporary Challenge Classification
- `SESSION_LOST_KEYWORDS`: Phải bao gồm các dấu hiệu mất phiên thực tế như `"account screen"`, `"login-issue"`, `"văng"`, `"session expired"`, `"logged out"`.
- `CHALLENGE_KEYWORDS`: Dành cho captcha, challenge tạm thời như `"captcha"`, `"checkpoint"`, `"verification"`, `"verify"`.
- Trong `evaluate_batch`:
  - `session_lost`: kiểm tra các máy dính `SESSION_LOST_KEYWORDS`.
  - `challenge_failures`: kiểm tra các máy không thuộc `session_lost` nhưng dính `CHALLENGE_KEYWORDS`.
  - Báo động riêng rẽ 2 khối trong `format_alert_message` để operator phân biệt rõ P0 văng tài khoản với captcha tạm thời trên fleet.

## 2. Execution Discipline: Scoped Grep & Budget Constraints
- **Cấm tuyệt đối grep đệ quy root `D:/Taadaa/`**: Sẽ quét qua hàng trăm GB venv (`python-envs/`), logs, node_modules và chắc chắn dính timeout 180s. Luôn scope vào thư mục cụ thể của repo: `grep -rn "pattern" D:/Taadaa/automation-core/src/`.
- Khi user chỉ định ngân sách tool calls chặt (ví dụ `<= 10 tool calls. Apply patch trực tiếp và chạy test ngay`):
  - Không đọc git log khảo cổ hay search diện rộng.
  - Đọc đúng vị trí code cần sửa (1 call) -> Patch trực tiếp (1 call) -> Chạy test kiểm chứng (1 call) -> Sync file (1 call). Hoàn thành trong 4 calls.
