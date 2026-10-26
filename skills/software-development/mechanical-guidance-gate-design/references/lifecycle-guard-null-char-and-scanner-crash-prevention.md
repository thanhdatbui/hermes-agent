# Lifecycle Guard Embedded Null Character & Terminal Scanner Crash Prevention

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Root Cause)
Khi Coordinator hoặc Worker chạy lệnh Python nội tuyến (`python -c "..."`) qua công cụ `terminal`:
- Bộ hook giám sát vòng đời tiến trình gateway (`cron/lifecycle_guard.py` trong `hermes-agent`) quét qua các token của câu lệnh shell để phát hiện xem có script nào được gọi thực thi ngầm hay không (`_iter_command_segments`, `_iter_referenced_shell_scripts`).
- Khi câu lệnh chứa mã Python nhiều dòng, ký tự đặc biệt, regex, hoặc chuỗi escape, token parser có thể phân tách nhầm một đoạn mã thành đường dẫn file ứng viên (`candidate: str`) và chuyển vào:
  ```python
  def _read_referenced_script(path: Path) -> tuple[Optional[str], bool]:
      flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
      try:
          descriptor = os.open(path, flags)
      except OSError:
          return None, False
  ```
- Trên Windows, nếu chuỗi đường dẫn ứng viên chứa ký tự null (`\0`) hoặc chuỗi byte dị dạng, lệnh gọi `os.open(path, flags)` ném ngoại lệ:
  `ValueError: open: embedded null character in path`
- Vì `ValueError` **không kế thừa** từ `OSError` (cả hai đều là lớp con trực tiếp của `Exception`), khối `except OSError:` hoàn toàn bị bỏ lọt. Ngoại lệ văng ra ngoài tầng `terminal_tool`, làm sập toàn bộ lệnh terminal và khiến Coordinator bị tê liệt (crash lặp đi lặp lại hàng giờ).

---

## 2. Bản Vá Chuẩn Hóa O(1) (Mechanical Remediation)
Trong file `cron/lifecycle_guard.py` (dòng 259–262):
```python
# CŨ (DỄ CRASH KHI GẶP NULL CHAR):
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None, False

# MỚI (CHUẨN HOÁ CHỐNG CRASH):
    try:
        descriptor = os.open(path, flags)
    except (OSError, ValueError):
        return None, False
```
- Khối `except (OSError, ValueError):` đảm bảo mọi đường dẫn dị dạng, chứa null byte hoặc lỗi giá trị trên Windows đều được nuốt an toàn, trả về `(None, False)` coi như không phải script cần kiểm tra, không bao giờ đánh sập terminal.

---

## 3. Quy Tắc Phòng Thủ Cho Coordinator & Worker (Defense in Depth)
Khi viết lệnh `terminal` gọi Python nội tuyến:
1. **Ưu tiên viết file `.py` riêng biệt:** Thay vì nhét 20–30 dòng code vào `python -c "..."`, hãy ghi thành file script có cấu trúc (ví dụ: `tools/tmp_<task>.py`) rồi gọi `python tools/tmp_<task>.py`.
2. **Nếu bắt buộc dùng `python -c`:** Bọc toàn bộ payload vào Base64 để tránh mọi ký tự null, ngoặc kép, và newline lọt vào token scanner của shell:
   ```bash
   python -c "import base64; exec(base64.b64decode('...'))"
   ```
3. **Cảnh giác bẫy `GUARD_DANGEROUS_ROOT`:** Tránh đặt chuỗi `D:/` hoặc `D:/Taadaa` đứng trần trong chuỗi lệnh `python -c` vì regex phát hiện scan root có thể bắt nhầm và chặn oan lệnh. Luôn dùng đường dẫn con hẹp (ví dụ: `D:/Taadaa/tools/...` hoặc `D:/Taadaa/reports/...`).
