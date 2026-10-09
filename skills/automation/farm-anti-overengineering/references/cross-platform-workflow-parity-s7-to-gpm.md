# Cross-Platform Workflow Parity: Kỷ Luật Kế Thừa Workflow Từ S7 Sang GPM / Web

## 1. Bối cảnh & Phản hồi từ User (User Correction)
- **Câu nói trực tiếp của User:** *"ủa cái này có script ở s7 r, thì mày áp dụng y workflow ở đó mà làm thôi, sao mệt thế nhỉ"*
- **Vấn đề cốt lõi:** Khi xây dựng hoặc sửa script tự động hóa trên GPM (Playwright/Chrome PC) cho một dịch vụ mà Farm đã vận hành trên Samsung S7 (ví dụ: đăng ký tài khoản ChatGPT qua Email+OTP, xử lý onboarding, vượt popup, v.v.), Agent có xu hướng tự phát minh lại form sequence, tự đoán các trường input, và vấp phải hàng loạt edge case (Age input thay vì Birthdate, nút modal Onboarding `[Continue]`, selectors Gmail bị collision).
- **Hậu quả:** 5–10 lượt dispatch worker thử-sai (trial-and-error), dính timeout 600s, false-positives, và làm gián đoạn tiến độ của User.

## 2. Nguyên Lý Bất Biến (Parity Invariant)
1. **Kiến Trúc Responsive & Backend Dùng Chung:**
   Các dịch vụ lớn (OpenAI / ChatGPT, Google, TikTok, Hotmail) sử dụng chung một hệ thống API/auth và thiết kế giao diện responsive giữa Mobile Web/App và Desktop Web. Mọi quy tắc nghiệp vụ, trường form bắt buộc, và chuỗi popup trên S7 đều tồn tại tương đương trên GPM PC.
2. **Kế Thừa 100% Logic Đã Kiểm Chứng:**
   BẮT BUỘC mở và đọc script S7 canonical tương ứng trước khi viết hoặc sửa bất kỳ dòng code nào trên GPM.
   - Script S7 tương ứng: `D:/Taadaa/register gmail/scripts/hook_chatgpt_register.py`, `social_reg_v1.py`, `gmail_reg_v10.py`.
3. **Các Thành Phần Cụ Thể Phải Kế Thừa Trực Tiếp:**
   - **Xử lý Onboarding Form (About You):**
     + Trên S7: Form yêu cầu Họ tên + Tuổi (`Age: 25`, tính bằng `calculate_age_from_dob(dob)` $\rightarrow$ gõ `str(age)`). Nếu script trên PC chỉ tìm ô ngày sinh (`birthdate`), OpenAI sẽ hiện lỗi đỏ *"Enter a valid age to continue"* và chặn luồng.
     + Giải pháp chuẩn: Kế thừa trực tiếp logic tính tuổi và điền cả `name` lẫn `age` (fallback `dob`).
   - **Xử lý Onboarding Modals / Popups:**
     + Trên S7: Sau khi tạo tài khoản xong, OpenAI luôn hiện modal *"You're all set / [Continue]"*, *"Làm quen với Giọng nói / Get started with Voice"*. S7 đã định nghĩa danh sách nút đóng: `["Continue", "Tiếp tục", "Bỏ qua", "Bắt đầu", "Let's go"]`.
     + Giải pháp chuẩn: Bổ sung đầy đủ danh sách dismiss button này vào vòng lặp chờ `#prompt-textarea` trên PC.
   - **Bộ Nhận Diện Thoát Auth & Sẵn Sàng (Ready Gate):**
     + Trên S7: Đã liệt kê các indicator nhận diện đăng nhập thành công vào chat: `"Free", "Welcome to ChatGPT", "Trò chuyện", "Khung chat", "Message ChatGPT"`.
     + Trên PC: Kiểm tra URL không còn `/auth/`, kết hợp mở rộng selector `#prompt-textarea, textarea[placeholder*="ChatGPT"], div#prompt-textarea, div[contenteditable="true"]`.

## 3. Checklist Điều Phối Trước Khi Viết Automation Trên GPM (Coordinator Gate)
- [ ] Dịch vụ này đã có script tương ứng trên S7 farm chưa? (Grep O(1) kiểm tra `D:/Taadaa/register gmail/scripts/` hoặc `D:/Taadaa/Tiktok_Reg/`).
- [ ] Đã đọc step-by-step logic của script S7 chưa (các form fields, tên nút, độ trễ, thứ tự các bước)?
- [ ] Script GPM đã sao chép đủ các trường nhập liệu (ví dụ: Full name, Age) và các modal dismiss buttons chưa?
- [ ] Đã khóa 2 tầng Hard Gate (Hard Gate 1: bắt lỗi OTP sai; Hard Gate 2: bắt buộc URL chính thức và ô prompt hiển thị) chưa?
