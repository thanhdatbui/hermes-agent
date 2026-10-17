# Tiered Workflow 3.0: Anti-Deadlock, Context-Pack & Automatic Absorption (17/10/2026)

## 1. Bối cảnh & Sự cố Deadlock Điển Hình (Treo 2 tiếng không sửa nổi 1 dòng code)

### Hiện tượng:
- User yêu cầu nâng cấp giao diện Sổ Bệnh Án Follow trên Dashboard cổng 1905 thành Master-Detail 2 cột rộng rãi.
- Tác vụ cần sửa ~100 dòng HTML/JS trong 1 file component.
- Coordinator bị chặn bởi rule T1 cũ: "Cấm tự sửa code > 15 dòng diff, bắt buộc dispatch Worker".
- Worker subagent bị siết trần cứng: "Hard budget <= 15 calls".
- Worker nhận task mò mẫm đọc file để lấy ngữ cảnh -> đốt sạch 14/15 calls chỉ để đọc code -> kích hoạt Fail-Fast ABORT_SCOPE mà chưa sửa được dòng nào.
- Coordinator lấy kết quả abort, tự tay viết 100% code hoàn chỉnh nhét vào prompt để dispatch Worker lần 2 với nhiệm vụ duy nhất là ghi file.
- Worker pool chạy model phụ (ag-gemini-pool-3) bị treo / timeout 600s mà không phản hồi.
- Kết quả: Hệ thống rơi vào vòng lặp bế tắc (deadlock), mất hơn 2 tiếng đồng hồ không sửa xong 1 dòng code.

---

## 2. Mổ Xẻ 4 Sai Lầm Kiến Trúc Từ Claude Code CLI

1. **Đếm gộp cả Đọc lẫn Ghi (Read vs Write conflation):**
   - Trần 15 calls cào bằng cả read lẫn write. Đọc file là chi phí lấy context bắt buộc, không phải lan man. Worker ngoan vẫn cháy budget vì phải đọc hiểu file.
2. **Đo sai rủi ro (Diff lines != Risk):**
   - Ngưỡng 15 dòng chỉ đo kích thước diff chứ không đo rủi ro thực tế. Sửa UI, component, template, fix bug logic nhỏ 50–80 dòng bản chất rủi ro rất thấp (không đụng DB, credentials, device lock, watchdog), nhưng lại bị cấm Coordinator tự làm.
3. **Nghịch lý giao việc ngược đời (Context inversion):**
   - Coordinator đã đọc hiểu file, thậm chí đã viết xong 100% code hoàn chỉnh, nhưng luật lại bắt đẩy cho một Worker mới tinh không có context, bắt nó đọc lại từ số 0 để làm mỗi việc... ghi file.
4. **Thiếu Trạng Thái Cuối (No Terminal State):**
   - Khi Coordinator bị cấm làm, Worker không làm nổi, rule cũ không nói rõ "vậy thì ai làm tiếp", dẫn đến vòng lặp re-dispatch đóng băng phiên.

---

## 3. Quy Chuẩn Tiered Workflow 3.0 Toàn Diện

### 🟢 T0 — Coordinator Tự Xử Lý An Toàn Trực Tiếp (Không Cần Dispatch Worker)
- **Điều kiện:** Tối đa <= 2 files, tổng thay đổi <= 80 dòng diff, có focused test hoặc verify < 30s.
- **Phạm vi áp dụng:**
  * Sửa UI, component, template, CSS, format hiển thị.
  * Sửa bug logic nhỏ, test fixture, mock data.
  * Docs, markdown, config text.
  * Rename, regex cơ học đã kiểm tra grep O(1).
  * Áp dụng / ghi đè đoạn code/patch đã được soạn sẵn hoàn chỉnh.
- **VÙNG CẤM TUYỆT ĐỐI (CẤM T0):** Các file hook bảo vệ hệ thống, credentials, env, database schema, device lock, watchdog, policy trung tâm, closeout gate.
- **Bỏ khóa cứng tích lũy 200 dòng:** Nếu tích lũy > 200 dòng trong 1 session, Coordinator ghi 1 dòng log Re-plan check xác nhận vẫn đúng scope ban đầu rồi tiếp tục, không khóa vô cớ.

### 🟡 T1 — Dispatch Worker Kèm Context Pack Bắt Buộc (Task >= 3 Files Hoặc > 80 Dòng)
- **Bắt buộc Context Pack:** Coordinator đã đọc file thì BẮT BUỘC phải trích đoạn code cần sửa + signature các hàm liên quan vào Context Pack. CẤM giao task mở bắt Worker tự mò file từ số 0.
- **Tách biệt ngân sách:**
  * <= 12 write/exec calls.
  * <= 8 read calls (trong allowlist). Đọc context không tính gộp vào write làm cháy budget.
- **Timeout trần:** 240s/lượt.
- **CẤM Coordinator làm ngược đời:** CẤM soạn xong code hoàn chỉnh rồi giao Worker chỉ để ghi file; đã soạn xong an toàn thì Coordinator tự áp dụng (T0).

### ⚡ Cơ Chế Absorption Tự Động (Tự Làm Nốt Khi Worker Gãy — TUYỆT ĐỐI KHÔNG XIN Ý KIẾN)
- **Kích hoạt KHI:** Worker fail lần 1 (do cháy budget calls, timeout 240s, hoặc abort scope) MÀ phần diff còn lại <= 80 dòng diff / <= 2 files.
- **Hành động:** Coordinator TỰ ĐỘNG tiếp quản, áp dụng code và chạy verifier để hoàn tất task.
- **KỶ LUẬT TUYỆT ĐỐI CẤM CLARIFY:** Phản xạ ném bảng trắc nghiệm hỏi User ("có tiếp tục không", "cho phép tự sửa không") bị coi là hành vi đùn đẩy trách nhiệm và gây lỗi treo phiên. Thực thi dứt điểm trong ngân sách đã cấp.

### ⏱️ Time-box Điều Phối Thực Tế (Căn Cứ Audit Log Lịch Sử Farm)
- **Task T0:** Tối đa 8 phút (quá 4 phút chưa pass verifier -> dừng phân rã hoặc đổi hướng).
- **Task T1:** Tối đa 18 phút (quá 9 phút chưa pass verifier -> kích hoạt Absorption hoặc leo thang ngay, cấm ngâm).
- **Pool Circuit Breaker:** Nếu 1 worker pool timeout hoặc 5xx liên tiếp 2 lần -> đánh dấu OPEN 30 phút, cấm retry cùng pool, chuyển thẳng sang Claude CLI / Absorption.

---

## 4. Thang Leo Thang Thực Chiến (Escalation Ladder 3.0)

```text
Worker Fail #1:
  ├─ Cháy Budget / Thiếu Context:
  │    • Nếu phần còn lại <= 80 dòng / <= 2 files -> COORDINATOR TỰ HẤP THỤ (Absorption) & verify ngay.
  │    • Nếu phần còn lại còn lớn -> Tách nhỏ scope, soạn Context Pack mới rồi re-dispatch lần 2 (CẤM dùng prompt cũ).
  ├─ Logic Sai (Test fail): Bắt buộc đổi contract, đính kèm lỗi test vào prompt lần 2.
  └─ Timeout / Pool Treo: MỞ POOL CIRCUIT BREAKER NGAY (ngắt 30p), chuyển sang Claude CLI hoặc Absorption, CẤM retry cùng pool.

Worker Fail #2 (hoặc Pool Breaker OPEN):
  ├─ Tác vụ cần suy luận logic / kiến trúc sâu -> Chuyển giao Claude Code CLI (qua quota gate).
  ├─ Tác vụ sửa code cơ học / đã rõ diff -> Coordinator tự hấp thụ (Absorption).
  └─ Bế tắc ngoại vi khách quan (mất kết nối, lỗi hardware) -> L3 BLOCKED có evidence thật.

L4 Clarify (Cực kỳ hạn chế):
  CHỈ dùng khi: Quyết định nghiệp vụ của User, thiếu quyền credentials, hoặc thao tác tốn tiền thật (SMS, proxy trả phí, captcha).
  CẤM dùng để xin phép L0-L2 hoặc trốn timeout.
```
