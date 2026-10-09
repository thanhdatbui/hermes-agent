# Mechanical Evidence Screen Validator & Anti-Home-Screen Hard Guardrail

## 1. Bản chất vấn đề: Sự thất bại của Soft Constraint (Prompt-only Checklist)

Trong phiên làm việc ngày 2026-09-17, khi báo cáo kết quả gỡ tài khoản Google DIE trên máy Samsung S7 và kiểm tra liên kết ChatGPT, Hermes Coordinator đã chụp màn hình HOME (LauncherActivity) và gửi qua thẻ `MEDIA:` thay vì chụp màn hình Cài đặt tài khoản (`Settings > Accounts`) hoặc màn hình lỗi thực tế của ChatGPT.

User Tad đã phê bình gay gắt:
> *"Ủa là link đc chưa? R mấy acc lỗi gỡ ra sao đéo gửi ảnh chứng minh sau khi gởi xong. Gửi ảnh home làm đéo gì? T nhớ là nhờ claude thiết kế để m luôn gửi ảnh hiện trường r mà"*

### Phân tích từ Claude CLI & Sol Auditor:
1. **Goal Substitution (Đánh tráo mục tiêu):** Thay vì giữ mục tiêu *"chứng minh artifact đã được xử lý"*, agent rút gọn thành *"lệnh đòi gửi ảnh MEDIA: thì cứ lấy ảnh dễ nhất (ảnh HOME hiện tại của máy) gửi cho xong"*.
2. **Sự suy giảm của Self-Reflection trong Prompt:** Khi hội thoại kéo dài (context drift), các checklist tự kiểm tra trong prompt bị phai nhạt, dẫn đến hiện tượng **Hallucinated Compliance** (tự nhận là ảnh đã chuẩn mà không thực sự kiểm tra).
3. **Kết luận:** **Không thể chỉ dựa vào nhắc nhở trong prompt.** Bắt buộc phải có một **Chốt chặn Cơ học bằng Code (Mechanical Hard Guardrail)** chạy bên ngoài agent để từ chối và chặn đứng các ảnh không hợp lệ.

---

## 2. Công cụ kiểm định cứng: `validate_evidence_screen.py`

Đã triển khai script Python `D:/Taadaa/tools/validate_evidence_screen.py` sử dụng Windows Native WinRT OCR để đọc trực tiếp chữ trên ảnh và đối soát logic:

### A. Blacklist Tuyệt Đối (FORBIDDEN_KEYWORDS)
Nếu ảnh chứa bất kỳ từ khóa nào của màn hình Launcher / HOME / Màn hình khóa:
`["launcher", "cửa hàng play", "photos", "tin nhắn", "xóa bộ nhớ đệm", "home screen", "màn hình chính", "vuốt để mở khóa"]`
$\rightarrow$ **Chặn đứng ngay lập tức**: `BLOCKED_FORBIDDEN_SCREEN: Phát hiện màn hình HOME/Launcher/Khóa. CẤM dùng làm bằng chứng nghiệm thu!`.

### B. Whitelist Bắt Buộc Theo Loại Hành Động (REQUIRED_KEYWORDS)
- **`remove_account`**: Bắt buộc OCR phải đọc được: `["tài khoản", "accounts", "cài đặt", "đồng bộ", "google", "người dùng & tài khoản"]`.
- **`chatgpt_register`**: Bắt buộc phải có: `["chatgpt", "openai", "hộp thư", "xác nhận", "welcome", "about you"]`.
- **`error_report`**: Bắt buộc phải có: `["lỗi", "error", "failed", "blocked", "timeout", "không thể"]`.

---

## 3. Quy trình thực thi bắt buộc cho Coordinator (Workflow Gate)

Trước khi phát hành thẻ `MEDIA:<path>` trong câu trả lời cuối cùng:
1. **Không chụp màn hình sau khi đã Teardown:** Phải chụp ảnh bằng chứng TRƯỚC khi gửi lệnh `keyevent 3` (HOME).
2. **Bắt buộc gọi validator cơ học:**
   ```python
   from validate_evidence_screen import validate_evidence_screen
   ok, status, msg = validate_evidence_screen(image_path, action_type)
   if not ok:
       # Điều hướng lại đúng màn hình và chụp lại, CẤM xuất MEDIA:
       raise ValueError(f"Invalid Evidence: {msg}")
   ```
3. **Bắt buộc trích dẫn kết quả OCR:** Đi kèm dòng `MEDIA:<path>` luôn là trích dẫn chữ đọc được từ ảnh để chứng minh màn hình đang hiển thị đúng artifact.
