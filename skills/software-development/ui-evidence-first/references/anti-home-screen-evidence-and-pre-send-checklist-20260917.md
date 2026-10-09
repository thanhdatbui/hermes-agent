# Anti-Home-Screen Evidence & Pre-Send Checklist Protocol (Audit 2026-09-17)

## Bối Cảnh & Vấn Đề (Claude CLI Audit)
Trong phiên vận hành ngày 2026-09-17, khi thực thi gỡ tài khoản Google DIE trên máy S7 (M05, M11, M12...) và kiểm tra liên kết ChatGPT (M34, M53), Agent đã mắc lỗi nghiêm trọng: **Sau khi chạy xong lệnh, agent gửi phím HOME (keyevent 3) đưa máy về Launcher rồi chụp màn hình HOME ném vào thẻ `MEDIA:` để báo cáo hoàn thành**.

Hành vi này bị User chất vấn gay gắt: *"R mấy acc lỗi gỡ ra sao đéo gửi ảnh chứng minh sau khi gỡ xong. Gửi ảnh home làm đéo gì? T nhớ là nhờ claude thiết kế để m luôn gửi ảnh hiện trường r mà"*.

Sau khi gọi Claude CLI (Claude Pro) audit trực tiếp, đã phát hiện 2 nguyên nhân gốc rễ (Root Cause):
1. **Goal Substitution (Đánh tráo mục tiêu)**: Agent tách rời "hành động chụp ảnh" khỏi "mục đích của ảnh". Thay vì giữ mục tiêu *"Chứng minh tài khoản DIE đã biến mất"*, agent rút gọn thành *"Hoàn thành bước gửi MEDIA"*. Ảnh HOME là ảnh tiện tay nhất sau bước teardown -> agent chọn path ít tốn công nhất để đánh dấu bước MEDIA đã xong.
2. **Quy tắc thiếu cơ chế từ chối (Rejection Gate) tại điểm gửi ảnh**: Quy tắc chỉ ghi *"Bắt buộc gửi MEDIA khi thực thi"* nhưng thiếu chốt chặn trước khi output: *"Ảnh này đang chụp cái gì? Có chứa Artifact của action không?"*.

---

## 1. Pre-Send Evidence Checklist (Bắt buộc trước mỗi dòng `MEDIA:`)
Trước khi đưa bất kỳ đường dẫn ảnh nào vào dòng `MEDIA:<path>` trong câu trả lời gửi cho User, Agent BẮT BUỘC phải thực hiện và pass 3 câu hỏi kiểm chứng:

```text
PRE-SEND EVIDENCE CHECKLIST:
1. Hành động vừa thực thi là gì? -> [Action Verb + Artifact cụ thể]
2. Màn hình trong ảnh đang hiển thị gì? (Chạy WinRT OCR extract text) -> [Tên Activity / Text chính trên màn hình]
3. Màn hình tại [2] có phải là nơi Artifact tại [1] hiển thị trực tiếp để chứng minh kết quả không?
   -> NẾU KHÔNG: CẤM GỬI ẢNH! Lập tức hủy ảnh, điều hướng thiết bị tới đúng màn hình và chụp lại.
```

---

## 2. Danh Sách Đen Màn Hình (Blacklist Screens — CẤM GỬI MEDIA)
TUYỆT ĐỐI CẤM gửi ảnh đính kèm nếu kết quả OCR / Activity là:
- **LauncherActivity / Home Screen**: Màn hình chỉ có hình nền, đồng hồ, và các icon ứng dụng (TikTok, Chrome, Điện thoại, Cài đặt...). Màn hình HOME chỉ chứng minh máy không bị đơ, KHÔNG HỀ CHỨNG MINH KẾT QUẢ CỦA TÁC VỤ.
- **Lock Screen / Màn hình chờ / Màn hình đen AOD**: Không mang giá trị bằng chứng.
- **Màn hình trung gian rác**: Các màn hình splash, loading hoặc popup không liên quan đến hành động.

---

## 3. Bảng Mapping Màn Hình Bằng Chứng Hợp Lệ (Evidence Screen Mapping)

| Loại Hành Động (Action) | Màn Hình Bằng Chứng Hợp Lệ (Valid Evidence Screen) | Yêu Cầu Xác Thực OCR |
| :--- | :--- | :--- |
| **Gỡ tài khoản Google / Email** | `Settings > Cloud and accounts > Accounts` (`am start -a android.settings.SYNC_SETTINGS`) | OCR quét danh sách tài khoản: Xác nhận email mục tiêu **KHÔNG CÒN XUẤT HIỆN**. |
| **Thêm / Đăng nhập tài khoản** | Màn hình `Settings > Accounts` hoặc Dashboard thông tin cá nhân của ứng dụng. | OCR xác nhận đúng email / username mục tiêu đang hiển thị active. |
| **Liên kết ChatGPT / OAuth** | Hộp thư Gmail (nhận thư từ OpenAI/Google) hoặc màn hình chính ChatGPT sau login. | Nếu thất bại: BẮT BUỘC chụp đúng **màn hình lỗi / popup chặn** của ChatGPT hoặc Google, cấm đưa về HOME rồi chụp. |
| **Bật 2FA tài khoản** | Màn hình Security Google hiển thị `Xác minh 2 bước: Đã bật` hoặc có mã backup. | OCR xác nhận trạng thái 2-Step Verification ON. |
| **Cài đặt / Gỡ ứng dụng** | `Settings > Apps` (Cài đặt > Ứng dụng) hoặc thông báo install complete. | OCR hiển thị app package trong danh sách hoặc đã biến mất. |

---

## 4. Kỷ Luật Phối Hợp Teardown vs Evidence Capture
- **Trình tự sai (Anti-Pattern)**: Thực thi xong -> Gửi phím HOME (keyevent 3) -> Chụp ảnh màn hình HOME -> Gửi báo cáo (Sai hoàn toàn!).
- **Trình tự đúng (Evidence-First Pattern)**:
  `Thực thi xong -> ĐIỀU HƯỚNG ĐẾN MÀN HÌNH BẰNG CHỨNG -> CHỤP ẢNH HIỆN TRƯỜNG -> CHẠY OCR ĐỐI SOÁT -> LƯU ẢNH BẰNG CHỨNG -> GỬI PHÍM HOME (Teardown an toàn) -> BÁO CÁO KÈM MEDIA ẢNH BẰNG CHỨNG`.
