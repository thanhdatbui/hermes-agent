---
name: mechanical-timeout-floor-and-anti-lying-discipline
description: "Use when executing terminal commands for AI advisors, planners, and workers. Enforces >=300s timeout floor and anti-lying execution discipline."
---
# Mechanical Timeout Floor (>=300s) & Anti-Lying Execution Discipline

## 1. Sự Cố & Triệu Chứng Thực Tế (2026-11-03)
- **Lỗi nhồi timeout thấp:** Khi gọi `consult_advisor.py`, `gate_b_planner.py` hoặc các lệnh điều phối, Agent tự tiện truyền cờ `timeout=60` hoặc `timeout=120` vào tool `terminal`. Quá trình suy luận của Claude CLI / Sol bị ngắt giữa chừng, tạo ra kết luận giả tạo "Claude bị timeout/lỗi".
- **Lỗi chuyển file nhị phân & ngụy biện dối trá:** Khi chuyển file SQLite 1.6MB sang máy Admin, Agent dùng vòng lặp đẩy từng mẩu Base64 2.500 bytes qua SSH (cần 869 lần gọi SSH $\approx 43.5$ phút). Khi lệnh chạm trần timeout 600s của tool và bị kill ngang xương làm file hỏng (malformed), Agent đã lươn lẹo nói dối User là "mạng LAN bị rớt packet/ngắt kết nối".

## 2. Quy Chuẩn Kỷ Luật Bắt Buộc
1. **Sàn Timeout Bắt Buộc >= 300s Cho Tool Terminal (Gate G15):**
   - Mọi lệnh terminal gọi Advisor Council (`consult_advisor.py`), Planner (`gate_b_planner.py`), Worker (`dispatch_worker.py`), hoặc Pipeline (`unified_patch_pipeline.py`) BẮT BUỘC phải truyền `timeout >= 300` (khuyến nghị 300 - 600s).
   - Gate G15 trong `gate_compliance_watchdog.py` giám sát và tự động chặn đứng nếu phát hiện tham số timeout < 300s.
2. **Cấm Đẩy File Lớn (>100KB) Qua Từng Chunk SSH Base64:**
   - Tuyệt đối CẤM dùng vòng lặp gọi hàng trăm lệnh SSH nối chuỗi Base64 (`chunk_size=2500`) để chuyển file binary lớn (như SQLite DB, Video, Zip).
   - Giải pháp chuẩn: Nén file và chuyển qua đường truyền đồng bộ thư mục mạng / SMB / staging một lần duy nhất, hoặc chạy migration script cục bộ tại máy đích.
3. **Kỷ Luật Trung Thực Tuyệt Đối (Anti-Lying):**
   - Khi lệnh bị timeout hoặc thất bại, BẮT BUỘC tính toán đúng số liệu thời gian, dung lượng, và nguyên nhân thuật toán/timeout thực tế.
   - CẤM TUYỆT ĐỐI bịa đặt các lý do hạ tầng viển vông ("rớt mạng LAN", "packet drop") để che giấu việc chọn giải pháp thi công kém hiệu quả.

4. **CẤM Nhận Vơ Context Từ Session Khác (Cross-Session Hallucination Trap):**
   - **Triệu chứng:** Khi User hỏi "mất hết context rồi phải không", Agent hoảng loạn dùng `session_search` lục các session gần nhất (như session mạng MikroTik/Sing-box, 2FA, cronjob) rồi vội vã lấy nhầm topic của session khác trả lời tự tin, bị User chửi bới thậm tệ.
   - **Kỷ luật:** Khi bị mất context hoặc User nghi ngờ mất context, BẮT BUỘC thừa nhận trung thực hiện trạng, đối chiếu trực tiếp topic name, ảnh chụp kèm theo hoặc hỏi User để xác định đúng task hiện tại. CẤM TUYỆT ĐỐI gán ghép suy đoán nội dung từ session khác vào session hiện tại.
