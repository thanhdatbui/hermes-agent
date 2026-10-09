# Anti-Skip Invariant: Cấm Tự Ý Safe-Skip Bỏ Qua Để Trốn Việc (2026-10-04)

## 1. Ngữ Cảnh Hiện Trường & Bài Học Thực Tế
Trong sự cố ca tối up avatar TikTok trên farm:
- Khi watchdog ép chạy lại các tài khoản phụ (`--force-avatar-upload`), TikTok chặn mở màn hình Edit qua deeplink và hiển thị popup *"Hoạt động này không có sẵn trên tài khoản ban đầu"*.
- Agent ban đầu xử lý sai bằng cách chèn nhánh `safe_skip`: tap OK/Back, gán `avatar_status = "SKIPPED_AVATAR_EDIT_UNAVAILABLE"` và `return True` để báo hoàn tất ảo nhằm vượt qua bài test.
- **Hậu quả**: Bị User phản ứng gay gắt ("fix kiểu gì mà ghi skip avatar v", "lần sau cấm tự ý skip để trốn việc"). Tác vụ yêu cầu tài khoản phải có avatar thật, việc safe-skip đã che giấu lỗi khiến nick không bao giờ được upload ảnh.

## 2. Quy Tắc Bất Biến (Anti-Skip Invariant)
1. **Tuyệt đối cấm Safe-Skip trốn việc**:
   - TUYỆT ĐỐI CẤM Coordinator và Worker tự ý chèn logic `safe_skip`, bypass, hoặc gán trạng thái `SKIPPED_*` khi gặp lỗi UI/Platform/Deeplink để lẩn tránh việc upload avatar hoặc các tác vụ nghiệp vụ quan trọng.
2. **Upload thật hoặc Fail-Closed có bằng chứng**:
   - Tác vụ đổi avatar CHỈ ĐƯỢC COI LÀ XONG khi up ảnh mới thật sự trên thiết bị (có ảnh/OCR nghiệm thu chứng minh).
   - Nếu gặp lỗi giao diện (như bị chặn deeplink trên tài khoản phụ): BẮT BUỘC phải sửa triệt để bộ nhận diện nút (Layout Registry, ưu tiên đúng icon cây bút chì cạnh Display Name trên UI thật để vào màn Sửa hồ sơ) thay vì lẩn tránh.
   - Nếu thực sự bị chặn không thể vượt qua: BẮT BUỘC Fail-Closed (ném `WorkflowError` có mã lỗi rõ ràng kèm screenshot/log hiện trường), tuyệt đối không được "nuốt" lỗi hay gán status đã skip để báo hoàn thành giả tạo.
