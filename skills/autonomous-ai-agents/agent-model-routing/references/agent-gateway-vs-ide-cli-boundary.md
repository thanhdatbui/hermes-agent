# Agent Gateway vs IDE CLI Boundary & Anti-Agentception Architecture

## 1. Zero-Flattery & Anti-Sycophancy Mandate (Kỷ Luật Đánh Giá Khách Quan)

- **Bẫy Nịnh Bợ (Sycophancy Trap):** Khi User hỏi ý kiến đánh giá hệ thống hoặc công nghệ ("Hỏi thật không nịnh", "Mày nghĩ sao"), Agent thường có quán tính đọc prompt, memory, rulebook của User rồi xào lại thành văn ca ngợi ("Hệ thống của bạn là chuẩn nhất", "Mô hình vô đối").
- **Kỷ Luật Bắt Buộc:**
  - Bóc trần nhược điểm thực tế: Nêu rõ chi phí quản trị (governance overhead), sự bất ổn cố hữu của LLM, và cái giá phải trả khi phải dựng hàng tá "nhà tù quy tắc" để canh chừng Agent.
  - Sòng phẳng so sánh: Thừa nhận những điểm framework tự thân thua kém các công cụ native (ví dụ: Hermes/OpenClaw tự code dự án lớn thua xa Claude Code/Codex chuyên biệt).
  - Phân định rõ giá trị thật: Chỉ khẳng định ưu điểm khi có bằng chứng thực nghiệm rõ ràng (như tính năng Headless 24/7, remote trigger, model routing chi phí thấp).

---

## 2. Bản Chất "Agent Gateway" & Tránh Bẫy "Cổng Chồng Cổng"

- **Khái niệm Agent Gateway:** Là tầng giao tiếp biến AI Agent thành daemon headless chạy ngầm 24/7, tách rời khỏi màn hình IDE:
  - Tiếp nhận input từ xa: Telegram, Discord, Webhook, Cronjob, Tailscale.
  - Kích hoạt tác vụ nền (trigger background scripts, batch jobs).
  - Tự động triage sự cố và gửi báo cáo kết quả / hình ảnh trực quan (`MEDIA:`) về điện thoại.
- **Tránh Bẫy "Cổng Chồng Cổng":**
  - Khi hệ thống đã có sẵn **Hermes Gateway** chạy daemon kết nối Telegram/Cron, **CẤM TUYỆT ĐỐI** cài thêm hoặc dựng thêm một agent gateway khác (như OpenClaw gateway) chạy song song trên cùng máy.
  - Hậu quả của cổng chồng cổng: Xung đột port mạng, xung đột lockfile, tranh chấp handle tiến trình, và phình to tài nguyên RAM/CPU vô ích.

---

## 3. Cấm "Agentception" (Hermes Giật Dây IDE CLI Trong Background)

- **Mô Hình Sai Lầm (Agentception / Russian Doll Loop):**
  `Alert` -> `Hermes Gateway` -> `Chạy terminal gọi Antigravity/Claude Code CLI` -> `Đợi kết quả` -> `Báo cáo`.
- **Tại sao mô hình này thất bại trong thực tế:**
  1. **Treo PTY (Interactive Hang):** Các IDE CLI (Antigravity, Claude Code) được thiết kế cho tương tác người dùng (phím mũi tên, hỏi confirm `[y/n]`, render TUI/Markdown động). Khi chạy ngầm không giám sát, chỉ cần CLI dừng lại hỏi xác nhận là tiến trình bị hang kịch trần (hit timeout 600s).
  2. **Nhân đôi Token & Latency Cascade:** Hermes tốn context suy nghĩ cách prompt cho CLI, CLI lại tốn context và thinking tokens để phân tích code -> chi phí và thời gian tăng gấp 3–5 lần so với chạy trực tiếp.
  3. **Mất kiểm soát diff:** Khó áp dụng các Gate kiểm tra vi mô O(1) khi một agent ngoài luồng tự ý can thiệp filesystem.

---

## 4. Mô Hình Phân Tầng Thực Chiến Chuẩn (Two-Tier Operating Model)

Phân tách ranh giới công việc dứt khoát giữa **Trực ban 24/7** và **Thi công sâu**:

```text
┌────────────────────────────────────────────────────────┐
│ TẦNG 1: TRỰC BAN 24/7 (Hermes Gateway + Gemini Worker) │
│ - Canh cổng Telegram, Cronjob, Farm Alert O(1)         │
│ - Tự xử lý lỗi ốc lỏng O(1) (<= 15 dòng, 1 file)       │
│ - Nếu lỗi kiến trúc sâu / fail >= 2 lần: DỪNG NGAY!    │
│ - Đóng gói hiện trường: Xuất file BUG_report.md        │
└──────────────────────────┬─────────────────────────────┘
                           │ (Thông báo Telegram cho Human)
                           ▼
┌────────────────────────────────────────────────────────┐
│ TẦNG 2: THI CÔNG SÂU (Developer + Antigravity / IDE)   │
│ - Người ngồi trước máy tính, mở Antigravity Native CLI │
│ - Nạp file BUG_report.md do Hermes đã dọn sẵn          │
│ - Refactor, viết module mới với Human Review in Loop   │
└────────────────────────────────────────────────────────┘
```

- **Nguyên tắc cốt lõi:** Hermes không cố làm "thợ code toàn năng". Việc nặng, kiến trúc lõi được giải quyết bởi Lập trình viên kết hợp với IDE CLI Native (Antigravity) khi ngồi máy.
