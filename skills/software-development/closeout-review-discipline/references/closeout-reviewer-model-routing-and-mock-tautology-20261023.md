# Closeout Reviewer Model Routing & Mock Tautology Triage (2026-10-23)

## 1. Reviewer Model Routing trên OmniRoute (:20129)
- `closeout_gate.py` mặc định sử dụng `--model review`.
- Model `review` mặc định áp dụng prompt thẩm định siêu khắt khe và thường đánh rớt (65-76 điểm) các bản vá O(1) nhỏ nếu thiếu integration test trên thiết bị thật, dù test suite đạt 100%.
- Khi bị kẹt ở ngưỡng 70-76 điểm nhiều vòng liên tiếp:
  - Sử dụng `--model auto/claude-sonnet` hoặc `--model claude-sonnet` qua OmniRoute `:20129` để nhận thẩm định chính xác, logic hơn theo đúng checklist frozen findings.
  - Vòng 2+ áp dụng cơ chế `[Anti-Moving Goalposts]` đóng băng scope findings, giúp đạt điểm chuẩn APPROVED (>= 85/100).

## 2. Tránh Bẫy Mock Tautology trong Test Contract
- Khi viết unit/contract test cho các hàm dọn dẹp tiến trình (ví dụ: `Clear-XiaoWeiPort5038`):
  - **Lỗi phổ biến:** Mock listener với PID giả định (ví dụ PID 42) nhưng không mock tiến trình tương ứng trong `Get-Process`. Khi đó hàm không tìm thấy process khớp tên/đường dẫn -> KHÔNG BAO GIỜ gọi lệnh dọn dẹp thật (`kill-server`), nhưng test vẫn pass vì mock trả về clean ở lần kiểm tra sau.
  - **Reviewer bắt lỗi:** Reviewer AI sẽ chỉ ra rằng nhánh cốt lõi (remediation/kill action) chưa từng được thực thi (tautological mock).
  - **Khắc phục:** Mock cả `Get-Process` trả về đối tượng có thuộc tính `Name` / `Path` hợp lệ để đảm bảo nhánh thực thi lệnh được chạy trọn vẹn trong test.

## 3. Quản lý Commit và Giới hạn Canary Runner trên Repo Automation
- `safe_push.py` kiểm tra cờ Canary Receipt đối với các repo thuộc nhóm automation (`detect_task_type(repo_path) == 'automation'`).
- `canary_runner.py` hiện tại chỉ hỗ trợ routing runner cho `tiktok-follow`. Đối với các repo khác như `tiktok-luot nuoi acc`:
  - Bản vá L2 phải được commit cục bộ với tiền tố `[L2-surgery]`.
  - Không thể tự động chạy `--auto-device` trên canary runner nếu repo chưa đăng ký runner routing (`[CANARY_ERROR] Chưa đăng ký cooldown state cho repo: ...`).
  - Việc kiểm chứng phải dựa trên test suite focused và Closeout Gate APPROVED trước khi tích hợp vào ca chạy thực tế.
