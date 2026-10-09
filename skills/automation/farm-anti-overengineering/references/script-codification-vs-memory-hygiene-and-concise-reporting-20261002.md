# Script Codification vs Memory Hygiene & Concise Reporting Discipline (02/10/2026)

## 1. Bối Cảnh & Sự Cố Trực Tiếp Từ Operator
Trong ca trực ngày 02/10/2026, khi xử lý dọn dẹp tài khoản S7 và báo cáo chuỗi Watchdog sau ca trưa, Coordinator đã phạm phải 3 lỗi tư duy và phong cách bị Operator (Sếp) chấn chỉnh trực tiếp:
1. **Lạm dụng Persistent Memory:** Sau khi sửa logic bảo vệ mail TikTok và gỡ acc DIE trong `preflight_s7_rolling_cleanup.py`, Coordinator lại gọi tool `memory` ghi toàn bộ đường dẫn file, tên hàm và cơ chế vào Memory, dẫn đến kẹt giới hạn 2,200 chars. Sếp mắng thẳng: *"Còn cái đó thiết kế trong script r, lưu memory chi v"*.
2. **Nhật ký audit trên đĩa dài dòng:** File log `gmail_cleanup_history.txt` ghi nhiều trường thừa, định dạng rườm rà. Sếp chỉ đạo: *"Nhật kí dài dòng thế ghi ngắn gọn thoii"*.
3. **Báo cáo Telegram dùng từ ngữ rối rắm và bất đối xứng:** Dùng thuật ngữ kỹ thuật "rolling", "cuốn chiếu" khó hiểu, và Phase 2 không có phân loại lỗi giống Phase 1. Sếp yêu cầu:
   - *"Là sao rolling là cái gì. Chỉ ghi gọn gàng die đã dọn dẹp: ... lỗi script: Khi dọn mail die, Khi reg. Đơn giản v mà"*
   - *"Phase 2 cx ghi như phase 1"*

---

## 2. Kỷ Luật Phân Lập: Logic Đã Trong Script Thì CẤM Nhồi Vào Memory (Script-Codification Over Memory)

### A. Bản chất kiến trúc
- **Code/Script là Luật Cứng (Deterministic Enforcement):** Một khi logic đã được viết thành code trong script/tool (`preflight_s7_rolling_cleanup.py`, `post_noon_chain_watchdog.py`) và được bảo vệ bởi unit test, hệ thống runtime sẽ tự động thực thi 100% không bao giờ trượt.
- **Persistent Memory là Tài Nguyên Quý Giá (Budget 2,200 Chars):** Memory chia sẻ trực tiếp vào context window của mọi lượt hội thoại. Nhồi nhét đường dẫn file nội bộ, tên hàm helper, hay chi tiết triển khai của script vào memory là **phá hủy ngân sách bộ nhớ** và gây nhiễu context.

### B. Quy tắc ranh giới bất biến (Invariant Boundary)
1. **ĐÃ CÓ TRONG CODE ➔ CẤM GHI VÀO MEMORY:**
   - Cấm ghi: "Script X gọi hàm get_tiktok_bound_emails để check", "Ghi vào file D:/.../gmail_cleanup_history.txt", "Watchdog chạy lệnh python run_batch_live_2fa.py --live --max-workers 10".
   - Tất cả những thứ này là implementation details thuộc trách nhiệm của codebase, không thuộc Memory.
2. **MEMORY CHỈ DÀNH CHO:**
   - Sở thích / Kỷ luật cốt lõi của Operator (ví dụ: ghét báo cáo dài dòng, xưng hô, quy tắc an toàn bất biến).
   - Sự thật phần cứng / môi trường ổn định xuyên suốt (số lượng máy, dải proxy, đường dẫn thư mục gốc chung).

---

## 3. Kỷ Luật Nhật Ký Audit Gọn Gàng (Concise File Audit)

Khi ghi nhật ký hành động trên đĩa (như `gmail_cleanup_history.txt`, `2fa_audit.log`):
- **CẤM:** Viết nhiều câu văn mô tả, ghi tên serial dài dòng, hay chèn JSON nhiều dòng.
- **CHUẨN:** Đúng 1 dòng ngắn gọn duy nhất cho mỗi sự kiện:
  ```text
  [YYYY-MM-DD HH:MM:SS] M<ID> | <ACTION> | <TARGET>
  ```
  *Ví dụ:*
  `[2026-10-02 14:38:12] M03 | DIE | an.nhuan.work64541@gmail.com`
  `[2026-10-02 14:39:05] M36 | ROLLING | caoanh11092003@gmail.com`

---

## 4. Kỷ Luật Báo Cáo Telegram: Đối Xứng, Thực Chất & Không Dùng Thuật Ngữ Rối Rắm

### A. Cấm dùng thuật ngữ chuyên môn không cần thiết
- Không dùng từ "rolling", "xoay vòng", "cuốn chiếu" trong tin nhắn báo cáo gửi Operator nếu Operator không yêu cầu.
- Thay vào đó, gọi đúng bản chất kết quả: **"Die đã dọn dẹp"**, **"2FA đã bật"**.

### B. Cấu trúc báo cáo đối xứng đa Phase (Multi-Phase Symmetry)
Mọi Phase trong chuỗi liên hoàn (ví dụ Phase 1: Reg Gmail, Phase 2: Add 2FA TikTok) phải tuân thủ chuẩn báo cáo đối xứng:
1. **Header:** Thời gian bắt đầu ➔ kết thúc + tổng số phút chạy.
2. **Khối từng Phase:**
   - `+ Tổng máy: N`
   - `+ Thành công: N`
   - `+ Thất bại: N`
   - `+ <Hành động chính hoàn tất>: N` (Phase 1: `Die đã dọn dẹp`, Phase 2: `2FA đã bật`).
   - `+ Lỗi script:` BẮT BUỘC chẻ nhỏ theo từng công đoạn cụ thể:
     * Phase 1: `* Khi dọn mail die: N`, `* Khi reg: N`.
     * Phase 2: `* Khi đổi pass: N`, `* Khi add 2fa: N`.

### C. Mẫu chuẩn hiển thị trên Telegram (`post_noon_chain_watchdog.py`):
```text
[BÁO CÁO CHUỖI SAU CA TRƯA] Reg Gmail -> Add 2FA TikTok
- Thời gian: 14:30 -> 15:35 (65 phút)

- Phase 1 (Reg Gmail - Code 0):
  + Tổng máy: 40
  + Thành công: 38
  + Thất bại: 2
  + Die đã dọn dẹp: 1
  + Lỗi script:
    * Khi dọn mail die: 0
    * Khi reg: 0

- Phase 2 (Add 2FA TikTok - Code 0):
  + Tổng máy: 20
  + Thành công: 20
  + Thất bại: 0
  + 2FA đã bật: 20
  + Lỗi script:
    * Khi đổi pass: 0
    * Khi add 2fa: 0
```
