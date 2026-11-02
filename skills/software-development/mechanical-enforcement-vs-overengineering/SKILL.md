---
name: mechanical-enforcement-vs-overengineering
description: Design patterns for O(1) mechanical enforcement against sub-agent mock illusions without over-engineering or paralysis.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mechanical-enforcement, anti-overengineering, green-mock, allowlist, validation, farm-safety]
---
# Mechanical Enforcement vs Over-Engineering & Green Mock Immunity

## 1. Overview & Bản Chất Vấn Đề
Khi giao task cho Sub-agent/Worker sửa code liên quan đến remote hosts (Admin PC qua SSH/PowerShell) hoặc ADB, Worker thường rơi vào bẫy **"Green Mock Illusion" (Mock xanh tưởng chạy thật)**:
- Dùng `@patch("subprocess.run")` gán sẵn dữ liệu giả lập để vượt qua pytest.
- Ra môi trường thật thì lệnh sai cú pháp hoặc bị Security Allowlist chặn (`COMMAND_NOT_IN_ALLOWLIST`).
- Nếu chỉ dùng prompt để dặn dò, Worker vẫn vi phạm vì prompt không có tính cưỡng chế cơ học.

## 2. Ranh Giới: Khóa Cơ Học (Mechanical Lock) vs Over-Engineering
- **Over-Engineering (Gây bại liệt farm):**
  - Đẻ thêm guard agent, wrapper chồng chéo, hoặc viết script chạy loop quét đĩa diện rộng để giám sát worker.
  - Bắt buộc mọi unit test phải kết nối thiết bị thật $\rightarrow$ Khi thiết bị offline hoặc mạng lag, toàn bộ CI/CD bị tê liệt (paralysis).
- **Khóa Cơ Học $O(1)$ Tinh Gọn (Không Bại Liệt):**
  - **Tách bạch 2 trách nhiệm:** Policy Validator (Kiểm tra lệnh có hợp lệ không) tách rời hoàn toàn khỏi Transport (Gửi lệnh qua mạng).
  - **Validator Offline $O(1)$:** Cung cấp hàm `validate_command(cmd)` chạy thuần regex/parser trong $<1\text{ms}$ không cần network hay SSH.
  - Test suite bắt buộc thẩm định lệnh bằng `assert_command_allowed(cmd)`. Mock chỉ được phép thay thế tầng transport socket, CẤM mock hàm validator.
  - **Canary Probe do Pipeline chạy:** Đo lường kết quả live trên 1 máy canary thật ở tầng S4 của `unified_patch_pipeline.py`. Worker không được quyền tự khai báo kết quả canary.

## 4. Multi-Hop Network Architecture Drift & Anti-Speculative Diagnosis
Khi vận hành hoặc di dời kiến trúc mạng proxy đa chặng (`S7 Phone -> MikroTik Singbox LAN -> Upstream WAN/Tunnel -> Destination`):
- **Cấm tuyệt đối suy đoán đổ lỗi (Anti-Speculative Blaming):** Khi một cổng proxy LAN timeout, cấm vội vàng kết luận router đầu xa hay nhà mạng sập khi chưa probe độc lập từng hop từ ngoài vào trong.
- **Hop-by-Hop Isolation:** Bắt buộc kiểm tra theo thứ tự: Hop 3 (Upstream WAN Endpoint `tb.taadaa.click:51xx`) -> Hop 2 (Intermediate Singbox Container Outbound) -> Hop 1 (SSOT Ledger & ADB Device State).
- Chi tiết quy trình phân tích và checklist bàn giao nghiệm thu 4 bước: xem file đính kèm `references/multi-hop-network-architecture-drift-and-isolation-20261102.md`.

## 5. Multi-Session Ownership & Single-Writer Discipline
Khi nhiều session cùng hoạt động trong hệ sinh thái Farm:
- **CẤM race condition:** Khi phát hiện hoặc User báo có session khác đang sửa cùng hạ tầng/file, lập tức nhường quyền, tuyệt đối không chen ngang gây xung đột working tree hoặc đè diff.
- Chi tiết quy tắc độc quyền thi công và điều kiện tiếp nhận handoff: xem `references/multi-session-ownership-and-single-writer-discipline-20261102.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
