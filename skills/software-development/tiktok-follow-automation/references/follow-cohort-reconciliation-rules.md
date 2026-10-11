# Quy tắc Nghiệp vụ Đối soát Follow (Follow Cohort Reconciliation)

## 1. Bản chất sự cố lệch số liệu (Root Cause & Anti-Pattern)
- **Sai lầm thường gặp (Net Delta toàn farm):**
  Lấy toàn bộ biến động `delta_following` của mọi tài khoản trong database cộng gộp lại:
  `total_delta_following = sum(all_accounts.delta_following)`
- **Hậu quả:**
  Nếu một tài khoản không chạy follow trong ngày (hoặc nghỉ dưỡng sinh) bị TikTok trừ 1 following do tài khoản đối phương bị ban/xóa (`delta_following = -1`), con số âm này bị cấn trừ oan vào tổng lượt cày follow của các máy đang chạy (`13 + 4 + (-1) = 16`).

## 2. Quy tắc khoanh vùng đối tượng (Follow Cohort Scope)
- **Chỉ đối soát trên các nick có phát sinh hành động trong ngày:**
  Khoanh vùng chính xác tập tài khoản có `internal_followed > 0` (hoặc có ghi nhận trong `daily_account_actions` của ngày đó).
- **Tuyệt đối không kéo nick rảnh vào đối soát:**
  Các nick không chạy follow hôm nay bị tụt/tăng following tự nhiên KHÔNG được tính vào delta đối soát tiến độ cày cuốc của bot.

## 3. Quy tắc trừ khi nick trong nhóm chạy bị nhả follow
- **Không dùng `max(0, delta)` để giấu lỗi:**
  Nếu chính tài khoản nằm trong nhóm chạy follow (`internal_followed > 0`) bị TikTok rollback/nhả follow khiến `delta_following` âm, lượt giảm này **BẮT BUỘC phải trừ thẳng vào tổng đối soát** để phản ánh đúng thực tế số follow ròng mà bot mang lại.
- **Công thức chuẩn:**
  ```python
  if has_active_follow:
      # Chỉ tính tổng delta của các tài khoản có lệnh chạy trong ngày
      if internal_followed > 0:
          total_delta_following += delta_following
  else:
      # Fallback khi chưa có dữ liệu bot chạy
      total_delta_following += delta_following
  ```

## 4. Dọn dẹp telemetry rác (Duplicate Session Prevention)
- Khi test watchdog hoặc chạy script nháp, nếu các session key tạm (`test_check`, `*_p1`) cùng ghi vào `session_account_actions` sẽ dẫn đến lỗi cộng dồn x3 (`SUM(internal_follows)` ra 42 thay vì 14).
- Phải đảm bảo session key duy nhất và dọn dẹp các session rác trước khi aggregate sang `daily_account_actions`.
