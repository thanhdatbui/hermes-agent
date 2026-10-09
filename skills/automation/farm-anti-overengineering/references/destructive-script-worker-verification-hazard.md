# Bẫy Worker Tự Ý Chạy Script Sát Thương Cao Khi Ad-hoc Verification

## 1. Sự cố thực tế (Incident 11/09/2026)
- **Bối cảnh:** User yêu cầu tạo script tắt máy khẩn cấp `shutdown_farm_emergency.py` để dùng khi mất điện.
- **Lỗi điều phối:** Coordinator giao worker subagent viết script và yêu cầu "Test chạy thử cú pháp".
- **Thực tế:** Worker subagent theo phản xạ ad-hoc verification đã vô tình chạy vào hàm `main()`. Lệnh `adb shell reboot -p` lập tức được gửi tới toàn bộ 80 máy phone farm, khiến cả dàn bị sập nguồn/văng kết nối hàng loạt.

## 2. Quy tắc Điều Phối Chống Tự Kích Hoạt Sát Thương
1. **Trong Prompt Dispatch của Coordinator:**
   - Khi task liên quan đến script nguy hiểm (shutdown, reboot, purge, drop db, wipe device):
   - **BẮT BUỘC cấm worker execute script thật.**
   - Verification CHỈ ĐƯỢC DÙNG `python -m py_compile <file>` để kiểm tra syntax hoặc unit test với hàm mock `subprocess.run` / mock adb.
2. **Safety Pin by Design (Chốt An Toàn trong mã nguồn):**
   - Mọi script sát thương BẮT BUỘC phải đòi hỏi cờ `--force` hoặc biến môi trường trước khi thực thi lệnh thật:
   ```python
   if __name__ == "__main__":
       if "--force" not in sys.argv:
           print("[AN TOAN] Yeu cau truyen co --force de thuc thi!")
           sys.exit(0)
   ```
   - Nhờ đó, dù worker có lỡ gọi `python script.py` để test, script cũng không gây hậu quả trên farm.
