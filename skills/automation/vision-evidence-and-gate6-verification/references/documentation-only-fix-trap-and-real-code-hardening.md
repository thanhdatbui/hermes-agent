# Bẫy Documentation-Only Fix & Kỷ Luật Sửa Mã Nguồn Thật Khi Lỗi Tái Diễn

## 1. Bối Cảnh Sự Cố & Dấu Hiệu Người Dùng
- **Hiện tượng:**
  1. Trong một session trước, Agent phát hiện lỗi Egress Leak (rò rỉ prompt kỹ thuật `[CONTRADICTION_GATE_TRIGGERED]` ra màn hình chat Telegram do gate quét nhầm câu nhận việc / giải trình).
  2. Agent viết bài phân tích rất chi tiết vào `references/egress-leak-and-reception-false-positive-remediation.md` và sync memory.
  3. Tuy nhiên, trên thực tế, file mã nguồn `guard_media_vision_gate.py` trên đĩa vẫn bị gỡ bỏ `EXEMPTION_MARKERS` (`# (EXEMPTION_MARKERS removed to prevent fail-open)`), code thực thi trên hệ thống không hề có bộ lọc miễn trừ.
  4. Ở session tiếp theo, khi Coordinator gửi câu tiến độ/khôi phục phiên không có thẻ `MEDIA:`, lỗi cũ tái diễn y hệt: một đoạn prompt thô dài ngoằng `[CONTRADICTION_GATE_TRIGGERED]` lại bị xả ra Telegram.
  5. User bức xúc gửi screenshot: *"Cái đụ mẹ session kia t fix r sao vẫn cứ spam ra 1 đống v"*.
  6. Coordinator thay vì kiểm tra git diff và sửa code, lại tiếp tục gõ văn xuôi giải thích nguyên nhân kỹ thuật. User lập tức phản hồi bằng dấu hỏi chấm: `"?"`.

---

## 2. Căn Nguyên Kỹ Thuật: "Explanation Theater" vs Code Reality
1. **Ảo giác đã sửa (Documentation Illusion):**
   - Agent nhầm lẫn giữa việc "đã hiểu và viết tài liệu" với "đã sửa và kiểm chứng mã nguồn thực tế".
   - Tài liệu kỹ thuật không thể chạy thay code Python trong runtime. Nếu code trên đĩa chưa sửa hoặc bị revert, runtime vẫn thực thi phiên bản lỗi.
2. **Nguy cơ Fail-Open khi cấu hình `EXEMPTION_MARKERS` quá lỏng:**
   - Trong quá khứ, một số kỹ sư đã xóa `EXEMPTION_MARKERS` vì lo ngại việc miễn trừ các từ đơn như `chuan hoa`, `cap nhat` sẽ làm fail-open các trường hợp báo cáo hoàn thành thật sự (`chuan hoa avatar`, `cap nhat avatar` mà không có ảnh).
   - Hậu quả của việc xóa sạch là mọi câu giải trình, thảo luận kỹ thuật, code, pytest, hoặc câu phục hồi phiên đều bị coi là claim UI và bị chặn fail-closed mù quáng.

---

## 3. Giải Pháp Kỹ Thuật Triệt Để O(1)

### A. Phân định ranh giới chuẩn xác cho `EXEMPTION_MARKERS`
Không miễn trừ từ đơn lẻ gây xung đột với action completion, mà chỉ miễn trừ các cụm từ ngữ cảnh rõ ràng:
```python
EXEMPTION_MARKERS = (
    # Nhận việc & Đang tiến hành
    "nhan lenh", "bat dau", "dang thuc hien", "dang kiem tra", "chuan bi",
    "ke hoach", "quy trinh", "huong dan", "chuan hoa cac kenh",
    "yeu cau", "tien hanh",
    # Giải trình kỹ thuật, thảo luận & phân tích
    "giai thich", "nguyen nhan", "ly do", "van de", "dieu tra", "phan tich", "overengineer",
    "gate", "hook", "watchdog", "prompt", "leak", "lo hong", "kien truc", "security theater",
    "tai sao", "vi sao", "thao luan", "tu van", "hoi dap",
    # Code & Git & Công cụ
    "script", "code", "ham", "function", "commit", "diff", "branch", "repo", "test", "pytest",
)
```
- Giữ vững `ACTION_COMPLETION_PATTERNS` chứa `chuan hoa`, `cap nhat` để các câu test như `chuan hoa avatar` (không có ảnh) vẫn bị chặn đúng spec.
- Giữ `EXEMPTION_MARKERS` cho các câu phân tích kỹ thuật (`giai thich`, `nguyen nhan`, `gate`, `script`, `pytest`...) để các câu hội thoại không bao giờ bị chặn oan.

### B. Kiểm chứng toàn diện bằng Unit Test
Sau khi sửa code trên đĩa, BẮT BUỘC chạy `python -m pytest D:/Taadaa/tools/tests/test_guard_media_vision_gate.py` đảm bảo **100/100 tests PASSED**.

---

## 4. Kỷ Luật Ứng Xử Khi User Phản Ứng "?"
1. Dấu hỏi chấm `?` của User là tín hiệu: *"Mày lại ngồi nói suông giải thích mà không bắt tay vào sửa?"*.
2. TUYỆT ĐỐI CẤM gõ thêm văn phân trần.
3. Lập tức kiểm tra diff, sửa file mã nguồn, chạy test pass, và báo cáo kết quả hành động cụ thể (Action & Evidence).
