# OS-Level State Invariants vs Heuristic Regex Gate Theater (2026-10-30)

## 1. Căn Bệnh "Gate Thrashing & Security Theater"
Hệ thống Coordinator từng gặp hiện tượng "fix hoài mà gate vẫn lì dù đã có auto-wire và guidance":
- **Nguyên nhân gốc rễ (Root Cause):** Hook gate sử dụng regex/heuristic bắt chuỗi trong lệnh shell hoặc prompt text. LLM là động cơ xác suất; chỉ cần thay đổi cú pháp, dấu nháy kép/đơn, hoặc flag lệnh là gate rơi vào 2 thái cực:
  1. *False Positive (Chặn nhầm):* Gây tê liệt điều phối (Analysis Paralysis / Freeze).
  2. *False Negative (Lọt lưới):* Coordinator lách qua được nhưng không kiểm soát được chất lượng.
- **Vòng xoáy Over-Engineering:** Khi Coordinator lách qua hoặc bị chặn nhầm, phản xạ sai lầm là tiếp tục viết thêm script auto-wire, thêm tầng guidance, thêm file lock tạm và receipt ký SHA256. Kết quả là chi phí bảo trì hệ thống kiểm soát vượt quá giá trị của sản phẩm nghiệp vụ ("tự đẻ rào rồi tự đi vá rào").

## 2. Tinh Gọn Về 4 Chốt Chặn Cơ Học Tầng OS (OS-Level State Invariants)
Thay vì đoán ý bằng regex, hệ thống quy chuẩn về 4 chốt chặn trạng thái cơ học đo đếm được ở tầng OS, không thể lách hay giả mạo:
1. **Vùng cấm tuyệt đối (Path Blacklist):** Chặn cứng mọi thao tác ghi/sửa vào `.env`, credentials, `SOUL.md`, `AGENTS.md`, `HERMES_SUBAGENT_RULES.md`.
2. **Ngân sách O(1) đo bằng Git:** `git diff --numstat` bắt buộc <= 30 dòng thay đổi và <= 2 files (bao gồm cả file test). Bất kỳ diff nào vượt quá 30 dòng đều bị reject cơ học, không cần đọc nội dung.
3. **Kiểm thử Focused bằng Exit Code:** Chạy đúng 1 lệnh test tập trung < 30s. Exit code != 0 là rollback ngay lập tức (`git checkout -- <file>`).
4. **Closeout Reviewer Độc Lập:** Reviewer chấm điểm độc lập (Closeout Gate) đạt Overall Score >= 85/100 mới được phép đóng phiên.

## 3. Phân Tầng Vai Trò & Cơ Chế Phán Quyết
- **Pipeline Sửa Code (unified_patch_pipeline):** Tự động 100% gọi Advisor cấp cao (Claude CLI / Sol) ở Stage 1 (Gate B Plan). Gemini Coordinator tuyệt đối CẤM tự ý lên plan sửa code.
- **Tranh Cãi Kỹ Thuật & Đánh Giá Độc Lập (On-Demand Advisor):** Khi User phát hiện Coordinator có dấu hiệu "nịnh hót", thiên vị hoặc chủ quan, User triệu hồi trực tiếp Advisor (`"gọi advisor"`, `"hỏi sol"`). Advisor độc lập (Claude Code `claude -p`) tiếp quản hiện trường và đưa ra phán quyết không thiên vị.

## 4. Chuẩn Hóa Action Card Bàn Giao (worker_card_report.py)
Loại bỏ hoàn toàn tường chữ và log giải trình lê thê. Mọi báo cáo nghiệm thu của Worker/Coordinator bắt buộc định dạng qua `python D:/Taadaa/tools/worker_card_report.py`:
- Trạng thái rõ ràng: SUCCESS / BLOCKED / FAILED kèm badge.
- Artifacts bàn giao cụ thể.
- Bằng chứng kiểm định (Focused test pass, Exit code 0, OCR/Vision mắt thật).
- Ranh giới an toàn Fail-Closed: Ghi rõ ĐÃ LÀM gì và CHƯA LÀM gì.
