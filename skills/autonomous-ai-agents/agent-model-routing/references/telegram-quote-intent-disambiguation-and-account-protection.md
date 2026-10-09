# Telegram Quote Intent Disambiguation & Account Lifecycle Protection

## 1. Bản chất sự cố nhầm lẫn (Root Cause)
Khi User điều hành đa tài khoản qua Telegram:
- Tin nhắn 1: User quote dòng thông báo về `Account A` (Pro) yêu cầu: "gắn lại acc này vào đúng pool pro cho tao".
- Tin nhắn 2 (nối tiếp ngay sau): User gửi tiếp: "acc này xoá khỏi pool free, tóm lại xoá khỏi omni route".
- **Bẫy suy luận mù quáng (Context Bleed):** Agent không phân tích rằng tin nhắn 2 là User đang nói về `Account B` (tài khoản Free bị lỗi/bị coi là rác mà User muốn loại bỏ), hoặc nếu tin nhắn 2 nói về việc loại bỏ tài khoản thì Agent phải đối chiếu danh sách tài khoản đang xử lý (`thanhdatbui1995` vs `alicelmoralesjvcrj`). Thay vào đó, Agent ngộ nhận "acc này" = tài khoản vừa được yêu cầu add vào Pro, dẫn đến việc xóa sạch credential quý giá `alicelmoralesjvcrj` khỏi hệ thống.

## 2. Invariant: Mapping Danh Tính Rõ Ràng Trước Khi Xóa (Anti-Deletion Ambiguity)
1. **CẤM TUYỆT ĐỐI** gọi API xóa (`DELETE /api/providers/:id` hoặc xoá DB) khi chỉ dựa vào đại từ mơ hồ ("acc này", "nó", "thằng này") trong chuỗi tin nhắn có nhiều tài khoản.
2. Khi User đưa ra 2 chỉ thị đối nghịch (Move/Rebind vs Delete):
   - BẮT BUỘC liệt kê rõ danh tính tài khoản đang gắn với từng hành động:
     * `Action 1 (Move to Pro)`: Xác định rõ email A.
     * `Action 2 (Delete from OmniRoute)`: Xác định rõ email B (ví dụ `thanhdatbui1995`).
   - Nếu chưa rõ "acc này" ám chỉ ai giữa 2 acc đang bàn, phải kiểm tra log/ngữ cảnh trước đó (ví dụ acc nào là Free dỏm bị loại, acc nào là Pro cần giữ) hoặc đối soát trước khi xóa.

## 3. Quy trình Khôi phục Cấp tốc từ OmniRoute SQLite Backup (Zero-Loss Recovery)
Khi lỡ tay xóa một tài khoản còn giá trị:
1. File backup tự động tại: `C:\Users\Kibe\.omniroute\db_backups\db_*.sqlite` lưu toàn bộ `access_token`, `refresh_token`, `proxy_assignments`.
2. Khôi phục trực tiếp bằng SQLite mà không cần quét GPM hay phiền User xác minh lại S7:
   - **Chú ý bẫy cú pháp SQLite**: Cột `"group"` trong `provider_connections` là từ khóa SQL dành riêng. Luôn dùng quoted identifiers `"{col}"` khi insert.
   - Khôi phục `proxy_assignments` với `scope_id = connection_id`.
   - Gắn connection vào đúng các combo mục tiêu (`ag-gemini-pool-3`, `ag-gemini-pool-3-37`) qua `PUT /api/combos/:id`.
3. Kiểm tra live probe bằng `POST /api/providers/:id/test` để xác nhận sống 100%.
