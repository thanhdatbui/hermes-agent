# Bẫy Hỏng Byte Screencap Khi Chạy Qua `with_device_lock.py` & Chuẩn 2 Bước Shell-Screencap + Pull (2026-10-15)

## 1. Bối cảnh & Hiện tượng thực tế (Incident Timeline 15/10/2026)
Trên hệ thống Taadaa Phone Farm, các thiết bị thật được bảo vệ bởi **Hard Gate #5 (Device Lock Required)**:
Mọi lệnh ADB trần như `adb -s <serial> ...` đều bị pre-execution guard chặn đứng nếu thiết bị chưa giữ lock hợp lệ trong `~/.codex/device-locks/`.

Khi Coordinator cần lấy bằng chứng ảnh hiện trường theo Gate 6, Coordinator dùng wrapper an toàn:
```bash
python D:/Taadaa/tools/with_device_lock.py --machine 50 -- adb -s ce091609dd78991305 exec-out screencap -p > /d/Taadaa/tmp/m50_current.png
```

### Triệu chứng lỗi (Failure Symptoms):
1. Lệnh trả về `exit_code: 0`, nhưng file ảnh `m50_current.png` chỉ có kích thước vỏn vẹn **340 bytes**.
2. Khi mở file kiểm tra bằng `read_file` hoặc `browser_vision`, hệ thống báo lỗi không đọc được ảnh:
   `Cannot read binary file 'D:/Taadaa/tmp/m50_current.png' (.png)`
3. Khi đọc vài dòng đầu của file (`head -n 5`), nội dung file hoàn toàn là **text UTF-8**:
   ```text
   [with_device_lock] Đang yêu cầu lock cho máy 50 (project=operator_tool, timeout=300.0s)...
   [with_device_lock] ĐÃ GIỮ LOCK thành công cho máy 50 (pid=32608, lock_id=bbde08fc)
   [with_device_lock] Bắt đầu thực thi: adb -s ce091609dd78991305 exec-out screencap -p
   [with_device_lock] Lệnh hoàn thành với exit code: 0
   ```

---

## 2. Căn nguyên kỹ thuật (Root Cause Analysis)
- `with_device_lock.py` là một Python script wrapper quản trị vòng đời lock của thiết bị. Khi hoạt động, script in các thông báo tiến trình (`Đang yêu cầu lock...`, `ĐÃ GIỮ LOCK...`) thẳng ra `sys.stdout`.
- Trong môi trường Git Bash / MSYS trên Windows, toán tử chuyển hướng shell `> file.png` sẽ gom toàn bộ luồng `stdout` của tiến trình Python ngoài cùng vào file đích.
- Khi lệnh con `exec-out screencap -p` xuất ra luồng nhị phân PNG, các byte nhị phân này bị trộn lẫn hoặc bị chèn sau các dòng log text của `with_device_lock.py`.
- Hậu quả: Header nhị phân chuẩn RFC của PNG (`\x89PNG\r\n\x1a\n` tại offset 0) bị phá hủy hoàn toàn. File trở thành text rác hoặc ảnh hỏng không thể render được, làm gãy toàn bộ chuỗi Gate 6 (Evidence-First Gate).

---

## 3. Quy chuẩn chụp ảnh 2 bước qua thiết bị (Canonical 2-Step Pattern)
Để đảm bảo ảnh nhị phân được truyền về host nguyên vẹn 100% mà không bị ô nhiễm bởi bất kỳ log banner nào từ Python wrapper:

### Bước 1: Lưu screencap vào bộ nhớ tạm của điện thoại (`/sdcard/`)
```bash
python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> shell screencap -p /sdcard/<filename>.png
```
*Lưu ý:* `adb shell screencap -p /sdcard/...` ghi trực tiếp file ảnh nội bộ trên Android, không xuất binary stream ra stdout của host.

### Bước 2: Kéo file ảnh về host qua lệnh `adb pull`
```bash
python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb -s <serial> pull /sdcard/<filename>.png <host_path>
```
*Lưu ý:* Lệnh `pull` chuyển file qua ADB protocol chuyên dụng, file ghi xuống đĩa host với hash SHA-256 nguyên vẹn, tách biệt hoàn toàn với log stdout của wrapper.

---

## 4. Checklist kiểm chứng bắt buộc trước khi gắn thẻ `MEDIA:`
1. **Kiểm tra kích thước file ảnh**: Ảnh chụp màn hình Android 1080x1920 chuẩn PNG phải có dung lượng từ **100KB đến 2.5MB**. Nếu file `< 10KB` (đặc biệt khoảng vài trăm bytes), đó là dấu hiệu dính text banner stdout ➔ BẮT BUỘC xóa file và chụp lại theo chuẩn 2 bước.
2. **Kiểm tra tính hợp lệ qua WinRT OCR / browser_vision**: Mở file ảnh kiểm tra trước khi gửi. Tuyệt đối không gửi ảnh mù khi chưa xác nhận ảnh mở được bình thường.
