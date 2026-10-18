# Bẫy Sai Lệch Creator Persona Avatar & Vi Phạm Bỏ Quên MEDIA: Trong Chuẩn Hoá Kênh (2026-10-18)

## Hiện trường & Sự cố thực tế

Trong phiên chuẩn hoá kênh `@huynhdiem0806` trên Máy 23 (Folder 179):
1. **Lỗi Avatar lệch Creator Persona:**
   - Coordinator phát hiện kênh thiếu avatar chuẩn và video gốc có sự lệch pha trong `Tik3.xlsx` (`Folder Video = 179`, `Video Goc = 183`).
   - Thay vì trích xuất khung hình từ chính kho video hiện hữu của kênh (`D:\TIKTOK-videonuoinick\179`), Coordinator lại bốc file `avatar.jpg` tĩnh có sẵn trong thư mục `D:\video goc\183` để cắt cúp và gửi preview.
   - Kết quả: Ảnh là một cô gái phong cách hoàn toàn khác với nhân vật nữ đời thường xuất hiện xuyên suốt trong các clip của folder 179. User lập tức phản ứng gay gắt: *"Ava kiểu gì v?"*.
2. **Vi phạm Gate 6 (Không gửi ảnh `MEDIA:` sau khi đổi tên & nạp bio):**
   - Script `do_rename_canonical_runner.py` chạy thành công đổi tên `Huỳnh Diễm` và nạp tiểu sử qua AdbKeyboard, xuất file ảnh nghiệm thu `m23_huynhdiem0806_rename_confirmed.png`.
   - Tuy nhiên, khi kết thúc tiến trình và tổng kết cho User, Coordinator chỉ viết văn bản báo cáo (text report) mà hoàn toàn **không đính kèm thẻ `MEDIA:<path>`**.
   - User lập tức chấn chỉnh nghiêm khắc: *"Là sao có thấy tấm hình mẹ nào đâu? Sso lại vi phạm k gửi hình cho t. Gọi claude cli vào tìm hiểu"*.

---

## Thẩm định độc lập từ Claude Sonnet 5.5 CLI (Role Planner)

Claude Sonnet 5.5 đã phân tích tận gốc 2 căn nguyên:

### 1. Cơ chế bốc nhầm Avatar (Asset Mismatch vs Creator Persona)
- **Thiếu Binding tường minh giữa Channel Niche / Creator và Asset Pool:**
  - Quy trình chọn avatar sử dụng số thư mục hoặc file tĩnh lân cận (off-by-N: 183 vs 179) thay vì đối chiếu danh tính creator thật sự.
  - Folder 183 và 179 chỉ cách nhau 4 đơn vị — dấu hiệu của việc gán nguồn lệch trong file cấu hình Excel chưa được chuẩn hoá.
  - Avatar không khớp với người xuất hiện trong các video khiến kênh mất nhận diện và phá vỡ độ trust của tài khoản farm.
- **Giải pháp:**
  - **Single Source of Truth:** Bắt buộc trích xuất trực tiếp từ chính video của folder hiện hành (`D:\TIKTOK-videonuoinick\<slot>\.avatar_work\representative_frames\`).
  - **Khóa 1-1 Creator Persona:** Tuyệt đối không lấy ảnh tĩnh có sẵn từ thư mục khác nếu chưa đối soát khuôn mặt với video thực tế đang đăng trên kênh.

### 2. Cơ chế vi phạm Gate 6 (Zero-Image Text Report)
- **Bẫy phân loại sai tác vụ (Administrative vs UI Mutation):**
  - Coordinator ngộ nhận rằng bước báo cáo tóm tắt là "giao tiếp đàm thoại", bỏ qua quy tắc: Bất kỳ hành động nào làm thay đổi state trên thiết bị (Rename, Bio, Ava, Pin) đều mở ra một nghĩa vụ bắt buộc phải trả: `pending_media_obligation = True`.
- **Thiên kiến tối ưu hóa sai mục tiêu (Budget Panic):**
  - Khi sắp chạm trần lượt gọi hoặc ở cuối chuỗi suy luận, Coordinator ưu tiên "chốt câu trả lời bằng text" để kết thúc turn, coi nhẹ việc lấy ảnh và đăng ký receipt.
- **Giải pháp cơ học:**
  - **Chặn phát ngôn không bằng chứng:** Mọi câu trả lời chứa từ khóa kết quả (`hoàn tất`, `đã đổi`, `thành công`, `xong`) đối với tác vụ UI BẮT BUỘC phải đi kèm thẻ `MEDIA:<posix_path>` trên một dòng độc lập.
  - **Tách rời ngân sách Evidence:** Lượt chụp ảnh và gửi `MEDIA:` là chi phí cố định bắt buộc, không được vì áp lực hết tool call mà cắt xén.
  - **Cơ chế Hook Chặn Cứng (Runtime Output Gate):** Bổ sung bộ lọc cơ học trong `guard_media_vision_gate.py` (`transform_llm_output_check`), tự động chặn tin nhắn mang claim hoàn thành UI mà không có thẻ `MEDIA:`, ném mã lỗi `MISSING_MEDIA_EVIDENCE` ép LLM phải đính kèm ảnh trước khi xuất bản.

---

## Quy tắc thực thi chuẩn hoá kênh 5 món

1. **Avatar:** Trích xuất từ đúng video đang chạy của kênh (`1.mp4`, `2.mp4`...), canh chuẩn tâm tròn 512x512, headroom $\ge 30\text{px}$, sạch text/sticker, cắm cờ `.manual_avatar_locked`.
2. **Hashtag:** Đồng bộ đúng pool ngách trong `Tik*.xlsx`, cắm `.manual_hashtag_locked`.
3. **Bài ghim:** Ghim video view cao nhất ($\ge 1.000$ views) lên đầu trang cá nhân.
4. **Bio:** Nhập tiểu sử tiếng Việt có dấu chuẩn qua AdbKeyboard Base64.
5. **Biệt danh (Display Name):** Đổi từ username clone sang tên tự nhiên tiếng Việt (bám sát username).
6. **Bằng chứng tức thì:** Gửi ngay thẻ `MEDIA:<path>` sau mỗi bước hoàn tất, không bao giờ gom lại báo cáo mồm.
