# Phạm vi sửa đổi & Quy tắc Scope Boundary (User Correction 2026-08-26)

## 1. Không dùng file dirty ngoài scope để từ chối task
- Khi nhận yêu cầu sửa đổi tính năng/rule cụ thể từ user (ví dụ: bổ sung cơ chế cooldown, sửa filter selection), nếu working tree đang có file dirty từ phạm vi khác (như uncommitted docs, manifest test, patch của luồng khác), **CẤM** tự ý kích hoạt STOP GATE từ chối làm việc hoặc bắt user phải clean working tree.
- **Quy tắc:**
  - Giữ nguyên vẹn các file dirty ngoài scope.
  - Chỉ tập trung sửa và patch trên đúng allowlist file thuộc phạm vi task được yêu cầu.
  - Khi test/commit, chỉ stage và verify đúng allowlist đó.

## 2. Recovery đúng STT — Không mở rộng sang Pending Batch
- Tuyệt đối không tự biến lệnh "recovery các máy lỗi" thành "chạy lại toàn bộ pending batch".
- Mọi thao tác rerun phải đọc từ danh sách máy lỗi cụ thể, không gọi lại full detector.
