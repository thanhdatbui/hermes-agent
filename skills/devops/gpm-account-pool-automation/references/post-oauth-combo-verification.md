# Post-OAuth Combo Verification & Append Checklist

Khi thực hiện nạp profile GPM, chạy pipeline OAuth S7 (`run_oauth_s7_pipeline.py`) và append target vào combo OmniRoute (ví dụ: `ag-gemini-pool-3` qua `append_to_combo_pool3.py`), cần lưu ý:

1. **Kiểm tra trạng thái kết quả Pipeline:**
   - Đảm bảo script exchange code thành công và status trong `D:\Taadaa\GPM auto\config\oauth_pipeline_status.json` thuộc key `omniroute_success` với `status: "HTTP_200_OK"`.

2. **Xác minh trực tiếp trên OmniRoute REST API:**
   - Luôn fetch `GET http://127.0.0.1:20129/api/combos` và kiểm tra combo mục tiêu (`ag-gemini-pool-3`).
   - Duyệt mảng `models` để chắc chắn `connectionId` của tài khoản vừa nạp đã nằm trong danh sách model target.
   - Nếu chưa có (ví dụ do race condition khi append đồng thời hoặc script chạy batch ngắt giữa chừng), chủ động gọi hàm append một lần nữa với connection ID cụ thể.

3. **Sao lưu đồng bộ:**
   - Đảm bảo file backup `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json` được ghi lại sau khi cập nhật thành công combo.
