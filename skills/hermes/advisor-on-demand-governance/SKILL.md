---
name: advisor-on-demand-governance
description: Use when configuring Advisor Sol. Enforces on-demand only.
---
# Advisor On-Demand Governance

## Core Principle
- **100% STRICTLY ON-DEMAND**: Never guess user intent. Never auto-append Advisor (Sol) responses to chat messages based on heuristic words (e.g., "tư vấn", "lời khuyên", "có nên", "theo mày", "đánh giá", "phân tích giúp") or sentence endings with question marks `?`.
- The user must explicitly summon Advisor Sol by name.
- **CẤM LỌC TỪNG TỪ (ERADICATE HEURISTIC GATES, DO NOT CHERRY-PICK WORDS)**: Tuyệt đối không tiếp cận theo hướng "xóa từng từ nghi vấn". Tiếng Việt đa dạng, xóa từ này thì câu hỏi kỹ thuật thông thường (ví dụ: *"canary xem cron có fix đc k ?"*) vẫn bị dính do dấu hỏi `?` hoặc cấu trúc nghi vấn. BẮT BUỘC xóa sạch 100% nhánh suy đoán cảm tính trong `_is_advice_request()` và `classify_advice_intent()`, chuyển thành công tắc so khớp cơ học: Chỉ kích hoạt khi chứa đích danh các từ khóa triệu hồi.
- **Phân Tầng Timeout Song Song Hội Đồng 3 Cố Vấn**: Tránh ngộ nhận Claude CLI/Sol chết khi chỉ có Gemini Argon nhả chữ; Sol và Claude cần timeout bậc thang 60-75s và lệnh gọi terminal cần 120-180s để gom đủ 3 luồng (xem `references/advisor-timeout-layering-and-parallel-triage.md`).
- **Sàn Timeout 200s Toàn Diện Cho Hội Đồng 3 Cố Vấn**: Đã chuẩn hóa toàn bộ timeout Sol, Gemini Argon, Claude CLI và bộ điều phối song song về mốc cân bằng 200s (`max_total_timeout=200s`, subprocess=200s, threadpool=200s) trong `consult_advisor.py`, vừa đủ dài để cố vấn phân tích sâu codebase vừa không để người dùng chờ đợi quá lâu.
- **Chống Đầu Độc Advisor & Nguyên Tắc Lời Nói User Là Ground Truth**: CẤM Coordinator mớm cung / nhồi nhét kết luận chủ quan vào prompt gửi Advisor (tạo đồng thuận giả để cãi lại User). Tránh bẫy over-engineering (cấm lọc từ khóa rác làm bại liệt hệ thống); bắt buộc tuân thủ giao thức trung lập RAW_FACTS + USER_OBSERVATION (chi tiết: `references/anti-advisor-poisoning-and-ground-truth-protocol.md`). Khi User khẳng định sự việc đã từng chạy/được fix ở session cũ, BẮT BUỘC tra cứu session_search kiểm chứng thay vì vội vàng suy đoán đổ lỗi ngoại vi.
- **Quy Tắc Độc Lập Multi-WAN Proxy Egress Binding**: Trên OpenWrt multi-WAN/macvlan (Xiaomi R3G), khi 16 cổng proxy bị dồn chung ra 1 IP duy nhất hoặc dính dải CGNAT `100.77.x.x`, nguyên nhân cốt tử là do thiếu directive `Bind $ip_addr` trong file cấu hình Tinyproxy. Khi được `Bind` đúng IP nội bộ của từng session PPPoE, mỗi port sẽ egress ra một IP Public riêng biệt ngoài Internet. Bắt buộc kiểm chứng bằng Math Assert ($\text{Unique IPs} == \text{Total Ports}$) trước khi báo hoàn tất.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
