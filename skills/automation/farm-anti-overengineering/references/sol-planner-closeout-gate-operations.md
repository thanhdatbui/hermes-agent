# Sol Planner & Closeout Gate Operations Guide

## 1. Gọi Sol Plan (Silent Brain :20129)
Khi có sự cố farm hoặc User yêu cầu **"Gọi Sol plan"**:
- **Script điều phối:** `D:/Taadaa/tools/sol_planner.py`
- **Lệnh chuẩn:**
  ```bash
  python D:/Taadaa/tools/sol_planner.py \
    --goal "<Mô tả lỗi và mục tiêu fix>" \
    --file "<Đường dẫn file code cần can thiệp>" \
    --flow-name "<tên_flow>"
  ```
- **Cơ chế:** Script kết nối OmniRoute `:20129` model `chatgpt-web/gpt-5.6-sol-high`, trả về `sol_plan_id`, danh sách `tasks` (T1..Tn) và `patch_contracts` đảm bảo anchor duy nhất $c==1$.

## 2. Nghiệm Thu Qua Closeout Gate (Sol Auditor Scorecard)
Trước khi commit & push master, chạy thẩm định chất lượng code:
- **Script kiểm định:** `D:/Taadaa/tools/closeout_gate.py`
- **Lệnh chuẩn:**
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo "<path_repo>" --base HEAD --skip-test --verbose
  ```
- **Tiêu chuẩn:** Phải đạt `Overall Score >= 85/100` (`VERDICT: APPROVED`). Nếu bị REJECTED vì thiếu Telemetry & Observability, bổ sung logging có cấu trúc rồi thẩm định lại.

## 3. Xử Lý Khi Kích Hoạt Deadman Switch (Hard Gate #0)
- **Dấu hiệu:** `[HARD GATE #0 - PROGRESS SUPERVISOR DEADMAN SWITCH] TIẾN TRÌNH BỊ ĐÓNG BĂNG!` do thăm dò quá 15 phút không tạo State Change.
- **Giải pháp:**
  - Không spam tool query hay cố xóa file thủ công.
  - Báo cáo User hiện trường & đề xuất Patch Contract $c==1$.
  - Thực hiện ngay một thao tác State Change thực sự: gọi `patch` file code cần sửa hoặc chạy lệnh compile/test qua terminal. Deadman Switch sẽ tự động mở khóa ngay khi ghi nhận State Change.
