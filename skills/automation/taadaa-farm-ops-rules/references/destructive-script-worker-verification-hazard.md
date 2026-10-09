# Bẫy Nguy Hiểm: Worker Tự Ý Chạy Script Sát Thương Cao (Destructive Tool / Shutdown / Reboot) Lúc "Ad-hoc Verification"

## 1. Hiện tượng & Sự cố thực tế (Incident 11/09/2026)
- **Bối cảnh:** User yêu cầu tạo script tắt máy khẩn cấp `shutdown_farm_emergency.py` để dùng khi mất điện.
- **Lỗi điều phối:** Coordinator dispatch worker subagent để viết script và yêu cầu "Test: chạy thử nghiệm cú pháp python script (dry-run)".
- **Thực tế xảy ra:** Worker subagent thay vì chỉ kiểm tra cú pháp AST (`python -m py_compile`) hoặc mock hàm `subprocess.run`, worker đã chạy script kiểm chứng thật gọi vào `main()` / hàm gửi lệnh.
- **Hậu quả:** Toàn bộ 80 máy phone farm nhận lệnh `adb shell reboot -p` ngay lập tức, văng kết nối khỏi Tiểu Vi, cả farm bị shutdown mềm đột ngột.

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Script có hiệu ứng vật lý sát thương (Destructive Side-effects):**
   - Các script liên quan đến `reboot`, `shutdown`, `rmdir`, `kill-server`, `pkill`, xoá DB, format, reset setting... nếu được thực thi trong quá trình worker làm việc sẽ gây hậu quả tức thì trên thiết bị thật.
2. **"Verification Reflex" mù quáng:**
   - Theo thói quen TDD / Ad-hoc verification, worker luôn muốn "chạy script để chứng minh nó hoạt động". Nếu prompt không cấm triệt để việc invoke code thật, worker sẽ chạy file vừa viết.
3. **Thiếu cơ chế Chốt An Toàn (Safety Pin / Dry-run Guard) trong mã nguồn:**
   - Script không có cờ `--force` hoặc biến môi trường `CONFIRM_SHUTDOWN=1`. Khi gọi hàm mà không có đối số, script mặc định chạy thẳng logic sát thương.

## 3. Quy tắc Bắt Buộc (Invariants) Khi Soạn Script Sát Thương / Khẩn Cấp

### A. Quy tắc trong Dispatch Prompt của Coordinator:
- Khi giao worker viết script nguy hiểm (shutdown, reboot, purge, drop db, wipe device):
  - **BẮT BUỘC cấm worker execute script thật:**
    > *"CẤM TUYỆT ĐỐI chạy script thật. Verification CHỈ ĐƯỢC DÙNG `python -m py_compile <file>` để kiểm tra syntax hoặc unit test với hàm mock `subprocess.run` / mock adb."*

### B. Quy tắc Thiết Kế Mã Nguồn (Safety Pin by Design):
Mọi script có khả năng tắt nguồn, khởi động lại, xoá dữ liệu diện rộng BẮT BUỘC phải có **Chốt An Toàn** mặc định:
```python
# Mẫu Chốt An Toàn Bắt Buộc
if __name__ == "__main__":
    if "--force" not in sys.argv and os.getenv("CONFIRM_EMERGENCY") != "1":
        print("[AN TOAN] Script nay co the tat toan bo thiet bi!")
        print("De thuc thi, yeu cau truyen them co: --force")
        sys.exit(0)
```
- Khi viết như vậy, dù worker có vô tình gọi `python script.py` để "test", script cũng chỉ in ra cảnh báo an toàn và thoát ngay, không bao giờ tự ý gửi lệnh sát thương ra ngoài farm.
