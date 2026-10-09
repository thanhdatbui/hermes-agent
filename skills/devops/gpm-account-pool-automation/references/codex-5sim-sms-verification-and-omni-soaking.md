# Codex OAuth CLI Verification & 5sim SMS Pool Operation Rules

## 1. Bản chất cơ chế OpenAI OAuth Codex & Phone Gate
- **OpenAI Web vs OAuth CLI**: Trên giao diện web thông thường (`chatgpt.com`), tài khoản có thể không bị hỏi số điện thoại sau khi đăng ký bằng email. Tuy nhiên, khi gọi quy trình ủy quyền client OAuth (`auth.openai.com/oauth/authorize?response_type=code&client_id=app_EMoamEEZ73f0CkXaXp7hrann...`), OpenAI gần như **luôn kích hoạt màn hình yêu cầu xác minh số điện thoại (`/add-phone`)** đối với các session mới tạo.
- **Không tự động biến mất khi ngâm 48h**: Không suy đoán rằng ngâm 48h sẽ làm biến mất form số điện thoại. Do đó, quy trình tối ưu là: **Đăng ký ChatGPT xong -> Thực hiện OAuth Codex và xác minh số điện thoại ngay trong cùng phiên profile -> Lấy token xong TẠM TẮT trên OmniRoute để ngâm an toàn**.

## 2. Tiêu chí chọn số thuê 5sim (Cost vs Success Rate)
- **Mức giá chấp nhận được**: Loanh quanh **$0.05 - $0.12** (~1.200đ - 3.200đ / số). Tuyệt đối không chọn các quốc gia đắt đỏ ($0.15 - $0.20+).
- **Tỉ lệ thành công 24h (`rate24`)**: Chấp nhận mức **>= 18% - 30%**.
- **Danh sách ưu tiên (Priority Fallback Chain)**:
  1. `vietnam` (`virtual47` / `virtual34`): ~$0.10 - $0.12 (khớp IP farm, giảm risk cờ gian lận).
  2. `argentina` (`virtual62`): ~$0.05 (rất rẻ, tỉ lệ ~30%).
  3. `philippines` (`virtual58`): ~$0.10 - $0.11 (được kiểm chứng trong lịch sử top orders).
  4. `england` (`virtual34`): ~$0.12 (kho lớn, tỉ lệ ~39%).
  5. `thailand` (`virtual34`): ~$0.08 (giá rẻ).

## 3. Vòng lặp thử liên tục & Cơ chế hoàn tiền (Continuous Retry & Auto-Cancel)
- **Cấm dừng lại khi 1 số không về SMS**: Khi một số bị timeout (sau 90s không nhận được OTP từ OpenAI), script **không được dừng lại báo lỗi ngay**.
- **Quy trình chuẩn**:
  1. Gọi ngay API hủy số `https://5sim.net/v1/user/cancel/{order_id}` để 5sim **hoàn trả 100% tiền về ví ngay lập tức**.
  2. Không reload toàn bộ trang làm mất context; điều hướng lại `/add-phone` hoặc xóa ô số điện thoại.
  3. Tự động bốc tiếp số thứ 2, thứ 3 theo chuỗi ưu tiên giá rẻ cho tới khi OpenAI nhận số và SMS OTP nổ về máy.

## 4. Chiến thuật "Tạm tắt trên OmniRoute để ngâm 48h" (Safe Soaking)
- **Vấn đề**: Tài khoản vừa tạo mà gọi request dồn dập vào API Codex sẽ bị OpenAI quét bất thường (Velocity Check / Fraud Score cao), dẫn tới revoke token hoặc ban tài khoản.
- **Giải pháp**:
  - Ngay khi nhận được `connection_id` từ callback port `1455`, script tự động chạy lệnh cập nhật database OmniRoute:
    ```python
    cur.execute("UPDATE provider_connections SET is_active = 0 WHERE id = ?", (connection_id,))
    ```
  - **Cronjob tự động kích hoạt sau 48h**: Thiết lập cronjob định kỳ quét database:
    ```python
    # cron_omni_activate_soaked_codex.py chạy mỗi giờ:
    # Nếu thời gian từ lúc codex_oauth_at >= 48 tiếng -> UPDATE is_active = 1
    ```
  - Nhờ đó, tài khoản hoàn tất toàn bộ thao tác OTP/sim nhạy cảm trên profile GPM, sau đó "ngủ" an toàn 48h trước khi hòa vào pool sản xuất.
