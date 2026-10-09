# Media Evidence Gate & Khắc Phục Bẫy "Khi Cần" (Sự Cố Quên Gửi Ảnh Nghiệm Thu Farm)

Ngày ghi nhận: 12/09/2026.
Tác nhân: Claude Code CLI Audit theo yêu cầu của Tad sau sự cố Admin Hermes Bot quên gửi ảnh kết quả chạy máy M246.

---

## 1. NGUYÊN NHÂN GỐC RỄ (ROOT CAUSES)

1. **Bẫy điều kiện mềm trong System Prompt ("Optional Loophole"):**
   - Các câu chữ cũ như *"Khi có yêu cầu ảnh máy N..."* hoặc *"Khi cần gửi ảnh máy N, dùng ADB screencap..."* tạo kẽ hở ngữ nghĩa cho LLM. Khi script trả về stdout `success`, LLM tự suy diễn rằng "task đã xong ngon lành, user không hỏi cụ thể nên lần này CHƯA CẦN gửi ảnh", dẫn đến việc cắt bỏ hoàn toàn bước gửi ảnh.

2. **Xung đột phân vai Coordinator vs Worker (Diffusion of Responsibility):**
   - Coordinator ở session chính bị giới hạn không chạm adb tay, ỷ lại Worker subagent đã làm xong.
   - Worker chạy trong subagent bị cô lập, không có kênh Telegram để gửi `MEDIA:`, chỉ ghi log text.
   - Hậu quả: Không bên nào sở hữu bước gửi ảnh cuối cùng cho User.

3. **Xung đột Budget & Tối ưu hóa Token:**
   - Khi token hoặc tool call budget cạn dần, LLM ưu tiên kết thúc core logic và xem capture/upload ảnh là bước "nice-to-have" nên tự động prune.

4. **Thiếu Gate kiểm soát nghiệm thu (Missing Enforcement Point):**
   - Các gate trước đây chỉ kiểm soát code diff, monolith anchor, commit, rebase, push mà không có gate nào xác thực sự hiện diện của thẻ `MEDIA:` trong báo cáo kết quả.

---

## 2. QUY TRÌNH & ĐIỀU LUẬT KHÓA CỨNG (INVARIANT CONTRACT)

### Điều 1: Bất biến nghiệm thu hình ảnh (Gate 6)
- **MỌI task can thiệp máy farm** (chạy batch, test, fix bug UI, farm alert, canary, recovery): Báo cáo kết quả cuối cùng **BẮT BUỘC PHẢI ĐÍNH KÈM THẺ `MEDIA:<path_anh_screencap>` ở dòng riêng biệt**.
- **CẤM TUYỆT ĐỐI** các cụm từ điều kiện "khi cần", "nếu có yêu cầu".

### Điều 2: Phân định trách nhiệm Worker - Coordinator
- **Worker (Subagent):** Sau khi chạy xong thao tác automation, BẮT BUỘC chụp screencap màn hình máy thật lưu local và trả đường dẫn tuyệt đối trong artifact output (`ARTIFACT_IMAGE: C:/Users/...`).
- **Coordinator (Main Session):** BẮT BUỘC kiểm tra đường dẫn ảnh từ Worker (hoặc tự chụp screencap O(1) qua ADB serial nếu Worker thiếu) và nhúng `MEDIA:<path>` vào tin nhắn báo cáo gửi User.

### Điều 3: Hard Reject báo cáo thiếu ảnh
- Báo cáo kết quả task farm mà **THIẾU** thẻ `MEDIA:` được coi là **VI PHẠM GATE NGHIỆM THU, TASK CHƯA HOÀN THÀNH**. Coordinator không được phép chốt phiên hay tuyên bố "Done".
