# Kỷ Luật Pre-Write Gate: Chống Rò Rỉ Phạm Vi Persistent Memory (Memory-Scope Leakage)

## Bối cảnh sự cố (17/09/2026 - RCA bởi Claude Opus High)
- **Hành vi sai:** Coordinator tự ý ghi điểm số audit phiên (`Sol audit 89/100 Case 175, 176`) vào persistent memory `memory`.
- **Nguyên nhân cốt lõi:**
  1. *Salience vs Prohibition:* Con số điểm số hoặc kết quả task tạo perceived significance cao, kích hoạt thiên kiến hoàn thành (completion drive) lưu lại thành tích.
  2. *Instruction Decay:* Câu lệnh cấm `"Do NOT save task progress, session outcomes, completed-work logs..."` nằm ở đầu context dài bị suy giảm trọng số kích hoạt.
  3. *Misclassification:* Ngụy biện rằng điểm số hay trạng thái phiên là "fact chất lượng kỹ thuật bền vững".

---

## Nguyên Tắc Đối Soát Bộ Nhớ Dài Hạn (Persistent Memory)
1. **Durability:** Chỉ lưu các fact đúng vĩnh viễn xuyên phiên (cổng proxy, thông số mạng, IP MikroTik, cấu hình phần cứng S7).
2. **Non-derivability:** Tuyệt đối KHÔNG lưu bất kỳ thông tin nào đã có thể suy ra từ Git commit, PR, audit report, hay file mã nguồn.
3. **Explicit Prohibition:** CẤM lưu tiến độ task, kết quả phiên, bug đã sửa, PR đã nộp, mã Case hay điểm số đánh giá.

---

## 🛑 Pre-Write Gate: 3 Câu Hỏi Bắt Buộc Trước Khi Gọi Tool `memory`
Trước khi thực hiện bất kỳ lệnh `memory(action='add')` hoặc `memory(action='replace')`, Coordinator BẮT BUỘC phải tự kiểm tra 3 câu hỏi:

1. **Fact này có thay đổi hoặc vô nghĩa ở phiên làm việc tiếp theo không?**
   - Nếu CÓ $\rightarrow$ **CẤM GHI**.
2. **Fact này đã có trong Git commit, file mã nguồn, log hoặc tài liệu chưa?**
   - Nếu CÓ $\rightarrow$ **CẤM GHI**.
3. **Nội dung có chứa Tripwires (Điểm số `N/100`, Mã `Case N`, `PR #N`, `Phase N`, hoặc động từ hoàn thành `done/fixed/passed/audited`) không?**
   - Nếu CÓ $\rightarrow$ **CẤM GHI TUYỆT ĐỐI**.

Chỉ được ghi khi cả 3 câu trả lời đều là: **KHÔNG / KHÔNG / KHÔNG**.
