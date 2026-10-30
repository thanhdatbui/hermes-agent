# Benchmark: OpenMausBot vs Hermes Agent & Anti-Glazing Lessons

## 1. Bối cảnh & Tín hiệu hiệu chỉnh
- Khi User đưa sản phẩm agent mã nguồn mở bên ngoài (OpenMausBot) và nghi ngờ Coordinator "nịnh hót", thiên vị cho Hermes.
- Coordinator gọi độc lập Claude Code (`claude -p`) làm Advisor phản biện công tâm.

## 2. Đối chiếu 2 hệ thống
| Trục so sánh | OpenMausBot (milind-soni/OpenMausBot) | Hermes Agent (Taadaa Coordinator) |
| :--- | :--- | :--- |
| **Bản chất** | GUI Wrapper chất lượng cao (Electron/React 19) bao bọc CLI local (claude/codex/grok). | Headless Coordinator tự động hoá sâu công nghiệp, vận hành qua Telegram/CLI/API. |
| **UX & Đóng gói** | **Vượt trội**: Giao diện chat danh bạ thân thiện, cài nguyên team bot qua Markdown Playbook + YAML. | Yếu hơn: Cần người hiểu sâu nội bộ để vận hành, không có app store bot. |
| **Tích hợp bên ngoài** | 500+ apps qua Composio OAuth (Gmail, Slack, Notion, GitHub...). | Tự viết connector nội bộ cho từng dịch vụ. |
| **Quy mô & Unattended** | Dựa vào Approval Cards (Allow/Deny) của con người -> Dễ gây Approval Fatigue, không chạy được đêm. | **Vượt trội**: Chạy 24/7 không người, điều khiển Android Farm hàng trăm máy, SQLite ledger, watchdog. |
| **Kiểm soát code & Hardware** | Giao phó cho CLI, không có pipeline kiểm thử riêng. | **Vượt trội**: Pipeline S0->S5, Emergency Surgery O(1), Gate 6 OCR mắt thật, Closeout Gate reviewer chấm điểm. |
| **Chi phí bảo trì** | Thấp, đẩy trách nhiệm duyệt cho người dùng. | Cao, tốn nhiều công sức bảo trì hệ thống gate/enforcer/lock. |

## 3. Bài học kiến trúc & Ứng xử
1. **Tránh bẫy so sánh lệch trục (Mismatched Axes)**: Không so sánh trực tiếp một sản phẩm consumer desktop với một hạ tầng công nghiệp headless. Phải phân tách rõ từng trục.
2. **Thừa nhận điểm yếu của hệ thống**: Không che giấu các lỗ hổng fail-open hoặc chi phí bảo trì rườm rà của hệ thống gate nội bộ.
3. **Tiếp thu ý tưởng đóng gói**: Mô hình đóng gói team bot bằng Markdown Playbook (YAML frontmatter) của OpenMausBot là kinh nghiệm tốt để Hermes chuẩn hóa phân vai worker/subagent sau này.
