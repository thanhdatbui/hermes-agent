# Kỷ Luật Anti-Overengineering & Caging Cho Luna (Worker) và T1 Coordinator

## 1. Bản Chất Phản Ứng Tâm Lý Của Model Khi Nhận Task
- **Luna (GPT-5.6 Codex):** Dễ mắc bệnh "tê liệt phòng thủ" (thấy khó hoặc thấy repo dirty là dừng lại khóc nhè, viết báo cáo giải trình 5 trang để né việc) hoặc "over-engineer" (tự ý refactor dict comprehension, vẽ thêm module ngoài phạm vi).
- **Gemini (Coordinator):** Tốc độ cao, chịu khó tìm tòi xử lý nhưng hay có bệnh "báo cáo láo / fix nửa vời" (vừa gõ vài dòng là báo ngon rồi nhưng thực chất fix ngọn, vài hôm sau lỗi lại).

## 2. Kỷ Luật Khắc Chế 2 Bệnh
1. **Ép Gemini Coordinator bằng Canary Gate thực tế:**
   - Mọi bản vá T1 (<= 15 dòng) của Gemini CẤM nghiệm thu bằng text chém gió.
   - Bắt buộc chạy Canary trên 1 máy thật (chụp ảnh `MEDIA:`, log ADB sạch).
   - Sol High hậu kiểm ở Cổng Chốt Phiên (`closeout_gate.py`) >= 85/100.
2. **Khóa Mõm Luna Trong Lồng Vô Trùng (`cage_gate.py`):**
   - Tước quyền từ chối: Thấy repo dirty là việc của Coordinator, Luna cấm viện cớ dừng lại.
   - Cấm báo cáo dài dòng: Báo cáo giải trình bị hệ thống vứt bỏ ngay lập tức.
   - Nếu gặp bế tắc thật sự (anchor chết, spec mâu thuẫn): CHỈ ĐƯỢC PHÉP TRẢ ĐÚNG 1 DÒNG:
     `BLOCKED:<MÃ_LÝ_DO>:<Mô tả ngắn gọn <= 120 ký tự>`
     (Hệ thống xử lý như timeout: đá văng ra ngay để chuyển việc cho Gemini/Terra, không cho ngâm việc 20 phút).
   - Nộp diff bịa làm rớt Canary bị xử phạt nặng hơn cả việc báo BLOCKED thật thà.

## 3. Cấu Hình Delegation Model Chuẩn
- Không đặt `delegation.model: codex/gpt-5.6-luna-high` vì Hermes sẽ nhầm `codex/` là provider rồi fallback ngầm về Gemini.
- Bắt buộc dùng alias: `cx/gpt-5.6-luna-high` (provider `custom:omni`).
