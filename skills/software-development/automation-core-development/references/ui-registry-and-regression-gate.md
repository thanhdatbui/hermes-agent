# UI Layout Registry & Regression Gate Pattern (automation-core)

## 1. Bản chất Regression Gate (Cổng chống hồi quy)
- **Định nghĩa:** Cơ chế kiểm thử tự động ép buộc mọi bản vá UI cho một thiết bị/biến thể mới (ví dụ: Máy 18, Máy 28) bắt buộc phải vượt qua toàn bộ ma trận tiêu bản (`dump.xml` + `expected.json`) của TẤT CẢ các thiết bị/biến thể cũ.
- **Mục tiêu:** Chấm dứt vĩnh viễn căn bệnh "sửa máy này thì mù máy kia, vá chỗ này thì thủng chỗ khác".

## 2. Vì sao cập nhật đồng loạt phiên bản APK KHÔNG giải quyết được bài toán UI?
1. **Server-Side Feature Flags / A/B Testing:** TikTok bật tắt tính năng và layout động từ server theo từng tài khoản, không phụ thuộc phiên bản APK cài đặt.
2. **Account Lifecycle & Profile State:** Tài khoản mới reg vs tài khoản ngâm nuôi lâu vs tài khoản Creator/Shop hiển thị header, tab và nút bấm khác nhau. Cùng 1 máy khi switch account giao diện có thể đổi ngay lập tức.
3. **Nguy cơ rụng phiên:** Cập nhật APK hàng loạt trên 80–160 máy thay đổi app signature đột ngột, dễ kích hoạt checkpoint bảo mật, văng session và bão OTP/2FA.

## 3. Kiến trúc Layout Registry Pattern trong `automation_core/ui/`
- **Decoupled Variants:** Mỗi biến thể UI là một class kế thừa `BaseLayout` có `Fingerprint` toàn màn hình:
  - Tọa độ chuẩn hóa tỷ lệ 0.0..1.0 qua `Node.rel(tree)` (vá H7: không lệch khi đổi đời máy/độ phân giải).
  - Điều kiện bắt buộc `required` và điều kiện loại trừ `forbidden`.
- **Fail-Closed dứt khoát:**
  - Nếu $\ge 2$ layout cùng khớp $\rightarrow$ Trả về `AMBIGUOUS_LAYOUT` và dừng lại an toàn (vá H6), cấm đoán mò hay tự ưu tiên layout cũ.
  - Nếu 0 layout khớp $\rightarrow$ Trả về `UNKNOWN_LAYOUT`, ghi nhận quarantine artifact (`dump.xml` + `screencap.png`), cấm đoán mò tọa độ click.
  - Nếu dump XML parse lỗi/rỗng/0 nodes $\rightarrow$ Ném `DumpInvalid` (vá H11), không nuốt thành `UNKNOWN_LAYOUT`.
- **Khóa mã băm `MANIFEST.lock`:** Khóa SHA256 các fixture đối soát với git HEAD/origin/main để ngăn chặn agent tự sửa đáp án test.

## 4. Chống hành vi trốn việc (Anti-Skip Hard Enforcement)
- **Bắt quả tang các pattern "Fake Pass / Safe-Skip":**
  - Gán trạng thái `status = 'SKIPPED_'`, `avatar_status = 'SKIPPED_'`, `action = 'safe_skip'`.
  - Nuốt lỗi & fake completion: `if edit_state == 'unavailable': return True`.
  - Nuốt ngoại lệ: `except Exception: pass`, `except: return True`.
  - Fake test assertion: `assert True`, `assert avatar_status == 'SKIPPED_'`.
- **Physical Pre-Commit Hook:** Cài đặt hook tại `.git/hooks/pre-commit` gọi guard với `--cached`. Git sẽ tự động ném Exit Code 1 và từ chối commit ngay tại máy local nếu phát hiện bất kỳ pattern trốn việc nào.
