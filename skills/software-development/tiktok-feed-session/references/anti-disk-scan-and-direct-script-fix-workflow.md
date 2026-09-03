# Anti-Disk-Scan & Direct Script Fix Workflow

## 1. Bản chất vấn đề (Anti-Pattern)
- Khi nhận cảnh báo `🚨 [MÁY N] DỪNG PHIÊN`, agent thường có phản xạ tự động đi tìm file log bằng cách quét đệ quy ổ đĩa (`os.walk`, `glob(recursive=True)`, `grep -rn`, `find`) làm treo session 900s.
- Khi bị nhắc nhở, agent lại dễ bị chệch hướng sang việc dùng lệnh `adb shell` can thiệp thủ công (bấm nút, vuốt, đổi settings bằng tay) thay vì sửa codebase.

## 2. Quy trình tinh gọn chuẩn xác
1. **Lấy hiện trường nhanh (0.5s):**
   - Chạy: `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc đọc trực tiếp file log nếu biết đường dẫn.
   - Tuyệt đối CẤM quét toàn ổ đĩa.
2. **Sửa code trong script (Codebase Fix):**
   - Mở đúng file script/flow phụ trách (`python_runner/flows/...`).
   - Sửa logic để script tự động phát hiện và vượt qua lỗi (auto-recovery).
3. **Chạy test & Commit:**
   - Chạy focused pytest (<30s).
   - Chạy Canary thực tế.
   - Commit & Push master.
