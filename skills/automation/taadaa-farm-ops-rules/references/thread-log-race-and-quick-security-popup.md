# Thread Log Race & Quick Security Popup Handling (TikTok Farm)

## 1. BẪY LỆCH LOG ĐA LUỒNG KHI ĐỐI SOÁT TÀI KHOẢN (THREAD RACE IN LOGS)
- **Hiện tượng**: Khi phân tích log của công cụ chạy song song hoặc log dùng chung (`social_reg_log.txt`), các luồng ghi log đan xen nhau. Agent dễ nhìn nhầm danh sách account của máy A (ví dụ Máy 20) tưởng là đang nằm trên máy B (Máy 48) và vội vã kết luận "máy ngậm nguyên dàn nick lạ / ký sinh".
- **Kỷ luật bắt buộc**:
  - TUYỆT ĐỐI KHÔNG chỉ dựa vào text log dùng chung để phán đoán trạng thái tài khoản trên máy.
  - BẮT BUỘC kiểm tra trực tiếp trên thiết bị bằng lệnh screencap/dump UI: mở Profile -> mở Account Switcher để xem danh sách tài khoản thực tế đang active trên máy.
  - Phải kiểm tra serial thực tế qua `adb -s <serial> get-state` và đối soát 1-1 với `taikhoan_run_safe.xlsx` và `Tik<N>.xlsx`.

---

## 2. POPUP BẢO MẬT TIKTOK MỚI (`quick_security`) GÂY `ACCOUNT_VERIFY_MISMATCH`
- **Hiện tượng**:
  - Khi TikTok mở Profile hoặc Switcher, TikTok thỉnh thoảng hiện modal: *"Hãy cùng kiểm tra bảo mật nhanh nhé"* (`quick_security_title`) kèm nút đóng X không nhãn (`[936,857][1056,989]`).
  - Modal này che khuất toàn bộ giao diện Profile khiến hàm kiểm tra tài khoản không nhìn thấy username mục tiêu và ném lỗi `ACCOUNT_VERIFY_MISMATCH` -> rơi vào `MANUAL_REVIEW`.
- **Giải pháp / Cơ chế**:
  - Trong `automation-core` (`src/automation_core/tiktok/benign_popup.py`), hàm `detect_quick_security_popup()` nhận diện modal này qua text *"Hãy cùng kiểm tra bảo mật nhanh nhé"* và nút đóng top-right không nhãn.
  - BẮT BUỘC phải đăng ký `or detect_quick_security_popup(root)` vào danh sách tổng của `detect_allowed_generic_popup(root)` để mọi consumer (Upload, Feed, Follow) tự động nhận diện và bấm nút X đóng modal ngay khi vừa xuất hiện.

---

## 3. CẦU NỐI TỰ ĐỘNG KHÔI PHỤC LOGIN CHO CÁC MÁY THIẾU TÀI KHOẢN
- **Vấn đề cấu hình cũ**:
  - File cấu hình upload (`config-machine-*.yaml`) từng lưu đường dẫn cũ không còn tồn tại: `D:\Taadaa\Tiktok_Reg-worktrees\automation-core-040-rollout-20260730\tiktok_login_v1.py`.
  - Batch launcher (`run_tiktok_upload_batch.ps1`) ở các bản cập nhật cũ từng bị cắt cụt nhánh gọi login handler khiến máy thiếu nick bị kẹt ở `LOGIN_RECOVERY_REQUIRED`.
- **Giải pháp chuẩn hóa**:
  - Sử dụng công cụ cầu nối trung gian: `D:/Taadaa/tools/recover_missing_tiktok_login.py`.
  - Cú pháp gọi chuẩn:
    ```bash
    python D:/Taadaa/tools/recover_missing_tiktok_login.py --machine <N> --account <username>
    # Hoặc tự tra cứu account theo hàng:
    python D:/Taadaa/tools/recover_missing_tiktok_login.py --machine <N> --row <1-8>
    ```
  - Cơ chế giành/kế thừa lock an toàn: Script tự động kích hoạt engine `D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py` với cờ `--allow-parent-lock` để kế thừa `device-lock` từ các tiến trình feed/upload nền tảng mà không bị xung đột lock.
