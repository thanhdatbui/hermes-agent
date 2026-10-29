# Skill Re-bloat & Automated Pruning Governance (29/10/2026)

## 1. Bản chất Hiện tượng Re-bloat (Tái phình to Context)
- **Hiện tượng:** Sau khi người dùng/agent tinh gọn các file `SKILL.md` (giảm từ 100 KB về 2 KB), qua nhiều phiên làm việc, các agent khác khi giải quyết sự cố lại tiếp tục tự ý append hàng loạt danh mục `references/...`, case study, hoặc log lỗi vào file `SKILL.md`.
- **Hậu quả:** 42+ file `SKILL.md` bị phình ngược lên 100 KB – 115 KB mỗi file. Mỗi khi agent nạp skill, context bị nhồi từ 30.000 – 60.000 tokens rác, đẩy tổng context session lên tới 250.000+ tokens, gây nghẽn LLM, lag session và tốn chi phí/quota.
- **Bẫy gọi file reference con (`skill_view file_path=...`):** Khi điều phối lệnh thường, nếu agent gọi đọc file con trong `references/`, toàn bộ nội dung file (hàng chục KB) sẽ bị lưu vĩnh viễn vào lịch sử `messages` (`role: tool`), kéo theo suốt 100-200 lượt trao đổi tiếp theo.

## 2. Kỷ luật Cơ Giới Hóa Thay Vì Lưu Memory
- **Quy tắc vàng:** CẤM lưu các chỉ thị hành vi cấm đoán suông vào `MEMORY.md` (e.g. *"Coordinator cấm gọi skill_view..."*). Prompt dặn dò sẽ bị model bỏ qua khi đổi model hoặc khi context dài, đồng thời làm cạn kiệt ngân sách memory (trần 2.200 ký tự).
- **Giải pháp cơ giới hóa 2 lớp:**
  1. **Script dọn dẹp cơ học (`auto_prune_skills.py`):**
     - Đặt tại `D:/Taadaa/tools/auto_prune_skills.py` và `hermes/scripts/auto_prune_skills.py`.
     - Quét đĩa 2 cấp thư mục (tuân thủ Guard, cấm `os.walk`), kiểm tra các file `SKILL.md > 3.5 KB`.
     - Tự động sao lưu bản gốc vào `D:/Taadaa/skills-prune-backups/<timestamp>/`.
     - Gọt bỏ toàn bộ các khối danh mục tham khảo `## References` dài dòng, thay bằng 1 dòng trỏ vào thư mục `references/` có sẵn; giữ trọn frontmatter và nguyên tắc cốt lõi $\le 2.8$ KB.
  2. **Cronjob Silent Watchdog (`hermes-skills-garbage-collector`):**
     - Job ID: `14ef6e6824ef`, chạy mỗi 6h (`0 */6 * * *`).
     - Cấu hình `no_agent: true` (0 token LLM, chạy thuần CPU).
     - Áp dụng Silent Watchdog: khi skills sạch gọn thì hoàn toàn im lặng (zero stdout, không spam Telegram). Chỉ báo cáo khi có file bị dọn dẹp.

## 3. Kỷ luật Thao tác của Coordinator
- **Tránh đọc tham chiếu tràn lan:** Với các tác vụ vận hành thông thường, Coordinator chỉ đọc sườn `SKILL.md`. Tuyệt đối không tự ý gọi `skill_view(file_path="references/...")` nếu không có yêu cầu điều tra chuyên sâu từ User.
- **Kỷ luật ngắt phiên (`/new`):** Khi chuyển đổi ranh giới công việc (từ triage farm sang check đơn hàng, cấu hình), chủ động mở session mới để giải phóng context lịch sử cũ tích lũy.
