# Farm Alert Triage: Cấm hỏi ngược User về Repo/Code & Phân loại Blocker Gộp

## 1. Bài học xương máu: KHÔNG BAO GIỜ hỏi User "Gửi code/repo ở đâu"
- **Triệu chứng sai lầm**: Khi subagent timeout hoặc gặp alert mà chưa xác định ngay được repo, Coordinator quay sang yêu cầu User gửi: *"Gửi giúp 1 trong 2 thứ: 1. Đường dẫn repo... hoặc 2. Tên script..."*.
- **Hậu quả**: Vi phạm nghiêm trọng tác phong Autonomous AI Coordinator ("biết đọc k", gây ức chế tột độ cho User).
- **Quy tắc bất biến**:
  - Toàn bộ codebase Farm nằm cố định trong `D:/Taadaa/` (gồm `automation-core`, `tiktok-luot nuoi acc`, `tiktok-follow`, `tools`, v.v.).
  - BẮT BUỘC tự kiểm tra `git log`, `git diff`, và các file `src/` hoặc `python_runner/` bằng inspection O(1).
  - Không bao giờ hỏi xin file code hay repo path từ User khi thông tin đã có sẵn trên hệ thống.

## 2. Pitfall: Nhãn gộp Blocker type đè Keyword Phân loại Alert
- **Hiện tượng**:
  - Script runner của `tiktok-luot nuoi acc` (trong `multi_machine_smoke.py`) gán `blocker_type = "login-gms-verification"` cho toàn bộ cụm auth/challenge/verification.
  - Khi xảy ra lỗi captcha/challenge (`error_message = "manual_challenge marker detected"`), `MachineResult.error_type` vẫn mang giá trị `"login-gms-verification"`.
  - Nếu hàm đánh giá (`batch_aggregator.py`) ghép chuỗi `f"{error_type} {error_message}"` để tìm `SESSION_LOST_KEYWORDS` (chứa chữ `"login"`), lỗi captcha sẽ bị gán nhầm thành **P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT**.
- **Giải pháp chuẩn**:
  - **Tách thứ tự ưu tiên**: Kiểm tra `CHALLENGE_KEYWORDS` trước trên `error_message` hoặc `error_type` thuần (loại trừ nhãn gộp `"login-gms-verification"`).
  - Chỉ khi không phải challenge/captcha và thực sự có từ khóa mất phiên (`logged out`, `văng`, `session expired`, `login screen`) thì mới kích hoạt P0.
