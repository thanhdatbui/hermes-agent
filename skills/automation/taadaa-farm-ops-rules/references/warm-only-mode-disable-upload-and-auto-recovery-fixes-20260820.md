# CHẾ ĐỘ CHỈ LƯỚT NUÔI KHÔNG ĐĂNG VIDEO & FIX RESOLVE AUTO-RECOVERY TRONG VENV (20/08/2026)

## 1. TẠM DỪNG ĐĂNG VIDEO (UPLOAD HOOK) TOÀN FARM — CHUYỂN SANG WARM-ONLY
- **Yêu cầu người vận hành (20/08)**: "chỉnh script chỉ lướt nuôi k đăng video luôn nhé (hiện đang tắt follow h tắt đăng video luôn)".
- **Cơ chế triển khai (`python_runner/flows/multi_machine_feed_session.py`)**:
  - Mặc định `ALLOW_CROSS_REPO_UPLOAD = False`.
  - Hàm `_run_upload_hook` tự động kiểm tra cờ an toàn:
    - Biến môi trường: `ALLOW_FARM_UPLOAD=1` / `true` / `yes`
    - Cấu hình: `safety.allow_farm_upload: true`
  - Khi cờ tắt (mặc định): Tự động ghi `upload_result.json` với `status = "skipped"` và `reason = "farm-upload-temporarily-disabled-by-operator"`, log an toàn và return ngay lập tức mà không gọi subprocess upload.
  - Toàn bộ ca nuôi 1..3 chuyển sang chế độ lướt feed khám phá + like/share tự nhiên, dưỡng nick và bảo vệ IP proxy mới.

## 2. FIX RESOLVE ĐƯỜNG DẪN AUTO-RECOVERY KHI CHẠY TRONG VENV
- **Hiện tượng**: Script alert gửi ảnh Banner Đỏ (Message 1) nhưng không tự kích hoạt AI Recovery Agent chạy ngầm.
- **Root cause**: Trong `automation_core/alerts.py`, `_AGENT_SCRIPT` dùng `Path(__file__).resolve().parents[3] / "tiktok-luot nuoi acc" / ...`. Khi chạy từ môi trường ảo `D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core\...`, `parents[3]` bị trỏ sang thư mục venv thay vì `D:\Taadaa` $\rightarrow$ `_AGENT_SCRIPT.exists()` trả về `False`.
- **Giải pháp chuẩn hóa (`_find_agent_script`)**:
  ```python
  def _find_agent_script() -> Path:
      candidates = [
          Path(r"D:\Taadaa\tiktok-luot nuoi acc\python_runner\ai_recovery\agent.py"),
          Path(__file__).resolve().parents[3] / "tiktok-luot nuoi acc" / "python_runner" / "ai_recovery" / "agent.py",
          Path(__file__).resolve().parents[2] / "tiktok-luot nuoi acc" / "python_runner" / "ai_recovery" / "agent.py",
      ]
      for c in candidates:
          if c.exists():
              return c
      return candidates[0]
  ```
- **Xử lý xung đột `PIL` do leak `PYTHONPATH`**: Thêm khối try/except dọn sạch `sys.modules['PIL*']` và lọc bỏ đường dẫn venv ngoài ra khỏi `sys.path` trước khi load lại PIL chuẩn.

## 3. THÊM BỘ NHẬN DIỆN POPUP QUYỀN VỊ TRÍ TIKTOK (`detect_location_permission_popup`)
- **Màn hình**: Popup *"Xem nội dung phù hợp và địa điểm lân cận"* với 2 nút *"Hủy"* và *"Mở cài đặt"*.
- **Xử lý**: Tích hợp vào `benign_popup.py`, nhận diện đúng cặp title + body + cancel button `android:id/button3` và tự động thực hiện tap nút *"Hủy"* để tiếp tục luồng lướt Feed mà không văng ra Settings.
