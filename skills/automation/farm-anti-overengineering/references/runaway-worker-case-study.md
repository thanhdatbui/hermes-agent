# Case Study: Phân Tích Sự Cố Runaway Worker & Khắc Phục Over-Engineering (05/09/2026)

## 1. Hiện tượng sự cố
- **Bối cảnh:** User yêu cầu điều tra lỗi script farm và tăng ký tự khi sinh username Gmail để tránh trùng lặp.
- **Hậu quả:** Worker chạy ngầm kéo dài gần 2 tiếng đồng hồ (tổng thời gian 8.007s và 8.419s, tiêu tốn 150 tool calls).
- **Phản ứng của user:** Bức xúc vì thời gian chờ đợi quá lâu ("ủa sao làm gì gần 2 tiếng ms xong v, lí do", "là cách làm đó là đúng hay là đã bị over engineer?", "k có rút kn quần què gì hết, cái t cần là rule repo, skill hermes, để ép làm cho chuẩn k bị over engineer").

---

## 2. Nguyên nhân cốt lõi gây Over-Engineering (Tool Churn & Runaway Loop)

1. **Test Inflation (Đẻ thêm test suite đồ sộ):**
   - Thay vì chỉ sửa logic ghép chuỗi của hàm `build_username` trong 15 dòng code, worker tự ý viết một file test mới toanh với 8 bài test chi tiết (`test_username_entropy.py`).
2. **Simulation / Monte Carlo thừa mứa:**
   - Worker chạy script mô phỏng sinh 10.000 username ngẫu nhiên để tính toán xác suất trùng lặp và entropy phân phối. Đây là việc hoàn toàn thừa mứa và lãng phí tài nguyên tính toán đối với script vận hành farm.
3. **Tạo Probe Script tạm trong `%TEMP%`:**
   - Tạo file runner tạm `hermes-verify-check-<pid>.py`, thực thi qua shell rồi xóa trong khối `finally`. Quy trình này làm tăng gấp đôi số lượt tool calls không cần thiết.
4. **Re-run Full Test Suite nhiều lượt:**
   - Chạy quét lại toàn bộ 105 - 112 unit tests của repo `register gmail` nhiều lần sau mỗi thay đổi nhỏ.

---

## 3. Bài học & Kỷ luật chuẩn hóa

1. **Khóa ngân sách theo Tier (Dynamic Budget):**
   - Tier 1 (Hotfix / hàm lẻ): Tối đa 15–20 calls, xong trong 10–15 phút. CẤM viết test mới, chỉ `py_compile` hoặc 1 assert tối thiểu.
   - Tier 2 (Flow bug): Tối đa 25–40 calls, xong trong 20–30 phút.
   - Tier 3 (Major): Chia nhỏ thành các Phase Milestone (<30 calls/phase).
2. **Mốc Checkpoint bắt buộc:**
   - Chạm 25–30 calls chưa xong bắt buộc dừng lại báo cáo tiến độ, cấm chạy âm thầm 100+ turns trong bóng tối.
3. **Ban hành đồng bộ:**
   - Quy tắc đã được đưa vào 32 file `AGENTS.md` / `PROJECT_RULES.md` trên 16 repo farm, Memory persistent của Hermes, và Skill `farm-anti-overengineering`.
