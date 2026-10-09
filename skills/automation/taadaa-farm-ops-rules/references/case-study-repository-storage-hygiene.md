# Kỷ Luật Lưu Trữ Case Study / Postmortem Kỹ Thuật (Farm Taadaa)

## 1. User Correction (12/09/2026)
- **User instruction:** *"Lưu ở repo ai tool chứ lưu skill chi v"*
- **Vấn đề cốt lõi:**
  - Agent có xu hướng tự động ghi chép postmortem và phân tích sự cố vào skill context (`~/.hermes/skills/...`), làm phình to context window và vượt quá giới hạn ký tự (100,000 ký tự của SKILL.md).
  - Kho tri thức vận hành thực tế của đội ngũ và codebase nằm trực tiếp tại các repository dự án:
    - `D:\Taadaa\AI-Tools\docs\` (đặc biệt là `farm-automation-cases.md`, `docs/infrastructure/mikrotik/`)
    - `D:\Taadaa\automation-core\docs\` (đặc biệt là `farm-automation-cases.md`)

## 2. Quy Tắc Phân Loại Nơi Lưu Trữ
1. **Lưu vào Repository Tài Liệu (`AI-Tools` / `automation-core`):**
   - **Tất cả** các trường hợp: Postmortem sự cố máy farm, lỗi mạng/proxy, phân tích giao diện UI/ATX, hướng dẫn cấu hình router/mikrotik, kỷ yếu case thực tế (Case NET-xx, Case UI-xx, Case 9x).
   - Phải ghi nhận vào file markdown trong repo tương ứng và `git commit` rõ ràng.
2. **Khi nào mới lưu / patch vào Hermes Skill:**
   - **CHỈ** khi có chỉ đạo rõ ràng từ User yêu cầu cập nhật skill hoặc khi cần cập nhật quy trình điều phối/kỹ năng vận hành chung mà các agent khác dùng làm hướng dẫn thực thi.
   - Tuyệt đối không tự ý viết các bản phân tích sự cố chi tiết của từng máy đơn lẻ vào SKILL.md làm phình context.
