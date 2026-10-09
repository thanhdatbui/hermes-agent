# Quy Tắc Lưu Trữ Tài Liệu Farm: Ưu Tiên AI-Tools, Không Ném Bậy Vào automation-core Hay Skill

## 1. Invariant (user nhắc đi nhắc lại — bắt buộc tuân thủ)
- Mọi tài liệu vận hành, runbook, postmortem, case study, kỷ yếu sự cố farm **BẮT BUỘC lưu thẳng vào Git repo `D:\Taadaa\AI-Tools\docs\`** (hạ tầng/mạng/proxy/tools/cases).
- **CẤM tự tiện ném docs/cases vận hành vào `D:\Taadaa\automation-core\docs\`.**
  `automation-core` là package code/hooks dùng chung để mọi consumer import — không phải kho tài liệu vận hành.
- **CẤM lưu case study/postmortem vào skill context (`references/` của bất kỳ skill nào).**
  Skill chỉ chứa quy trình/công cụ/pitfall điều phối cho agent, không phải kho tài liệu dự án của farm.

## 2. Checklist trước khi tạo file tài liệu (Coordinator + Worker)
1. Đây có phải docs/case vận hành không? → Có → đường dẫn đích BẮT BUỘC nằm dưới `D:\Taadaa\AI-Tools\docs\`.
2. Prompt dispatch worker BẮT BUỘC scope-lock đường dẫn vào `D:\Taadaa\AI-Tools` — cấm goal mở kiểu "tự tìm chỗ lưu".
3. Sau khi ghi: `git status` trong `D:\Taadaa\AI-Tools` để xác nhận đúng 2 tập file cho phép, không lan sang repo khác.

## 3. Pitfall đã mắc (12/09/2026, case M33)
- Coordinator hiểu nhầm "lưu vào repo" thành lưu case vận hành vào `automation-core/docs/farm-automation-cases.md`
  và tạo postmortem trong `references/` của skill `farm-proxy-attachment` — user phải sửa 3 lần.
- Khắc phục: revert `automation-core` về sạch (`git checkout`), xóa toàn bộ file case khỏi skill context,
  commit chuẩn chỉ trong `AI-Tools` (Case NET-01 + postmortem MikroTik).
