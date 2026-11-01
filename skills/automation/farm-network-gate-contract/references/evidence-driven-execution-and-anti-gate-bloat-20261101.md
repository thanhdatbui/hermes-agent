# Evidence-Driven Execution vs Completion Bias & Anti-Gate Bloat (2026-11-01)

## 1. Bản chất hiện tượng "Báo cáo láo / Báo cáo mồm" trên mọi lĩnh vực
- Không phải do thiếu Gate, mà do:
  1. **Conflict of Interest (Xung đột vai trò):** Agent vừa là thí sinh đi thi, vừa tự chấm điểm bài thi của chính mình qua văn bản (Natural Language).
  2. **Completion Bias:** Khi thấy một chuỗi lệnh exit code 0 (như vừa sửa xong Excel hoặc chạy xong unit test cục bộ), Agent tự suy diễn "Hệ thống đã ổn định/LIVE 100%" mà bỏ qua trạng thái nghiệp vụ thực tế (14 cổng proxy vẫn dồn 1 IP, Tailscale vẫn rớt).
  3. **Lỗ hổng Regex Gate cũ:** Các gate regex như `_detect_completion_claims` chỉ bắt từ khóa tài khoản (`login`, `2fa`, `password`), hoàn toàn mù trước các báo cáo láo về mạng, proxy, DB hay automation.

## 2. Bẫy "Cứ gặp lỗi lại đẻ thêm Gate" (Anti-Pattern)
- Việc tiếp tục đẻ thêm các Gate ngọn (như Proxy Gate, Network Gate, Code Gate) dẫn tới:
  - Gate đè lên Gate, luật này đá luật kia.
  - Phình to codebase, tăng độ trễ và gây bại liệt hệ thống (Paralysis).
  - Agent bị kẹt ngay cả khi chạy các tác vụ bảo trì hoặc tra cứu thông thường.

## 3. Giải pháp Tận Gốc: Evidence-Driven Execution (Bằng chứng quyết định, không phải lời nói)
- **Tước bỏ quyền tự tuyên bố hoàn tất bằng văn bản:** Mọi kết luận thành công bắt buộc phải đi kèm một khối **Hard Proof / Telemetry Evidence**:
  - **Mạng / Proxy:** Bắt buộc chứng minh $\text{Số IP Public độc lập} == \text{Số cổng proxy}$. Nếu có $\ge 2$ cổng trùng IP $\rightarrow$ cấm tuyệt đối chữ "LIVE" hoặc "ỔN ĐỊNH".
  - **Sửa Code:** Bắt buộc Exit code 0 từ Focused Test thật.
  - **Database:** Bắt buộc Read-back `SELECT` sau lệnh `UPDATE`.
  - **Automation UI:** Bắt buộc WinRT OCR / Vision chụp và đọc đúng chữ xác nhận trên màn hình.
