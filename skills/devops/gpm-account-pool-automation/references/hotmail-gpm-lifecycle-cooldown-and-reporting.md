# Hotmail -> GPM Lifecycle: Cooldown Auto-Unblock & Multi-Stage Reporting

## 1. Lifecycle State Machine Architecture
Trong quy trình tự động hóa tài khoản Hotmail qua GPMLogin:
`HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `CODEX_OAUTH` -> `WAIT_7D` -> `CHANGE_INFO` -> `DONE`

Mỗi stage sở hữu tài nguyên profile riêng và phải tuân thủ nghiêm ngặt cách ly theo proxy port của từng máy farm.

## 2. Cơ Chế Auto-Unblock Sau Cooldown (Anti-Permanent-Lock)
- **Vấn đề**: Khi đăng nhập Hotmail thất bại (do mạng, Microsoft challenge, hoặc rate limit tạm thời), tài khoản bị đánh dấu `BLOCKED`. Nếu supervisor chỉ có điều kiện chặn cứng `status in {"BLOCKED", "FAILED"}`, các tài khoản này sẽ bị kẹt vĩnh viễn (starvation/deadlock).
- **Quy tắc Cooldown 48h (2 ngày)**:
  - Microsoft có cơ chế tự mở lại sau 24-48 giờ đối với các cảnh báo đăng nhập bất thường.
  - Scheduler/Supervisor định kỳ mỗi tick cần kiểm tra:
    ```python
    if stage == "HOTMAIL_LOGIN" and status in {"BLOCKED", "FAILED", "ERROR"}:
        fail_time = parse_time((info.get("last_result") or {}).get("at") or info.get("updated_at"))
        if not fail_time or (now_dt and (now_dt - fail_time).total_seconds() >= 2 * 86400):
            stage = info["stage"] = "HOTMAIL_LOGIN"
            status = info["status"] = "PENDING"
    ```
  - Khi được unblock về `PENDING`, tài khoản tự động được xếp vào hàng đợi FIFO và bốc chạy khi proxy port của máy rảnh. Nếu vẫn lỗi, nó quay lại `BLOCKED` và bắt đầu chu kỳ 48h mới.

## 3. Quy Tắc Báo Cáo Định Kỳ Nhiều Giai Đoạn (Anti-Truncation Bias)
- **Vấn đề**: Khi một stage có số lượng lỗi áp đảo (ví dụ Codex OAuth lỗi 198 nick do thiếu số VN), danh sách rút gọn `top 15` sẽ nuốt trọn toàn bộ các lỗi ở các stage khác (như 33 nick Hotmail Login), khiến người vận hành tưởng rằng không có lỗi ở các stage kia.
- **Giải pháp**:
  - BẮT BUỘC gom nhóm lỗi theo từng `stage` (`[HOTMAIL_LOGIN]`, `[CODEX_OAUTH]`, `[CHATGPT_REG]`).
  - Mỗi stage in từ 3-5 nick đại diện kèm máy, email và chi tiết lỗi thực tế, kèm số lượng còn lại.
  - Bộ đếm `DONE`: Kiểm tra cả `stage == "DONE"` lẫn `status == "DONE"` để tránh sai lệch khi supervisor lưu trạng thái hoàn tất chu kỳ.
