# Blueprint: Transitioning from Prompt Prose to Mechanical Code Gates

## Core Principle
> **"Anything an agent can only be reminded about is a wish, not a rule."**
> *(Bất cứ điều gì chỉ được dặn bằng lời nhắc trong prompt thì đó chỉ là điều ước, không phải là luật).*
> **Luật thật sự phải là một Gate cơ học nằm tại Choke Point (điểm nghẽn không thể đi đường vòng) mà Agent không có quyền vượt qua.**

---

## 1. Năm Điểm Chặn Cơ Học (Hook Points) Trong Hệ Thống Agent
1. **PreToolUse Hook:** Chặn trực tiếp tại runtime trước khi tool thực thi (kiểm tra arguments, tham số, file cấm, cấm broad scan, cấm subagent sửa code khi chưa có contract O(1)).
2. **Shell AST Parser:** Chặn tại tầng Terminal/Bash/PowerShell. Phân tích cú pháp cây AST thay vì dùng regex đơn giản để triệt tiêu các thủ thuật lách lệnh (aliases, subshells, `-EncodedCommand`, payload trong `python -c`).
3. **Domain Wrappers (Choke Point cốt lõi):** Thu hồi quyền gọi các primitive nguy hiểm trực tiếp (ADB trần, Excel direct write, logout trần). Bắt buộc mọi thao tác phải đi qua domain wrapper có lock, xác thực và audit logging.
4. **OS / File ACLs (Tự bảo vệ Gate):** Các file hook, policy và settings phải được hash-pinned hoặc set Read-Only với user của agent, ngăn cản agent tự viết script đè lên hoặc vô hiệu hóa gate của chính mình.
5. **Stop / Closeout Gate:** Chặn agent tự ý tuyên bố "xong việc" hoặc thực hiện `git push` nếu thiếu artifacts vật lý (ảnh nghiệm thu, OCR readback, test suite 100% pass, điểm reviewer).

---

## 2. Bảng Phân Loại & Chuyển Hóa 6 Nhóm Quy Tắc (Rules Taxonomy)
- **Nhóm A: Cú pháp (Syntactic):** Lệnh cấm tuyệt đối (cấm gõ mật khẩu, cấm reset --hard, cấm os.walk/find trên ổ đĩa, cấm cmd.exe). Chuyển thành PreToolUse/Shell AST hook deny, xóa 100% khỏi prompt.
- **Nhóm B: Trạng thái (State Predicate):** Phụ thuộc runtime (device lock, khoảng cách ca nuôi >= 60p, quota Claude < 85%). Chuyển thành State Gate kiểm tra trạng thái thực tế trước khi cấp quyền chạy.
- **Nhóm C: Bằng chứng hoàn thành (Completion Evidence):** Nghiệm thu đầu ra (ảnh MEDIA:, WinRT OCR, pytest pass, reviewer APPROVED). Chuyển thành Stop Hook & Closeout Gate.
- **Nhóm D: Quyền hạn bất biến (Capability Invariant):** Cấm logout nick lạ, cấm ghi đè cột Excel sai quy định. Đưa cứng vào thư viện lõi (Core Library constraints).
- **Nhóm E: Ngân sách / Bộ đếm (Budget & Counter):** Timeout terminal <= 60s, diff <= 30 dòng, turns cap <= 15. Chuyển thành Counter Hook cưỡng chế ngắt khi vượt ngưỡng.
- **Nhóm F: Nhận định & Văn phong (Judgment):** Tránh over-engineering, không báo cáo dài dòng, hỏi gì đáp nấy. Đây là nhóm DUY NHẤT được giữ lại trong Prompt.

---

## 3. Lộ Trình Cắt Giảm Prompt Siêu Tinh Gọn (Prompt Diet Roadmap)
1. **Mã hóa Gate (Codification):** Viết script hook kiểm tra và test tự động.
2. **Actionable Denials:** Khi Gate chặn, thông báo lỗi phải chỉ rõ đường đi đúng (paved road) để agent tự sửa mà không cần dặn dò trước trong prompt.
3. **Prompt Diet:** Xóa sạch văn bản răn đe tương ứng trong AGENTS.md, PROJECT_RULES.md và SKILL.md.
4. **Just-in-Time Injection:** Chỉ tiêm rule vào context đúng tại thời điểm agent gọi công cụ liên quan.
