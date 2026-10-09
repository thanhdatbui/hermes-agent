# Taskbar Mystery Icon Triage: Active Dialog vs Pinned Shortcut Trap (2026-10-08)

## 1. Hiện Tượng & Bài Học Thực Tế
User gửi ảnh chụp màn hình máy tính hỏi: *"cái app gì nằm dưới taskbar màu trắng như lỗi v bấm vào k mở lên đc"*.
Agent mắc sai lầm nghiêm trọng (Bị User mắng *"Vẫn còn taskbar có icon trắng kìa??? Đkm Mày có thực sự coi hình trc khi tl tao k thế"*):
1. **Sai lầm phán đoán vội vã:** Agent tự ý nhảy vào `%APPDATA%\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar` quét các shortcut `.lnk` bị ghim. Thấy `Comet.lnk` bị mất file chạy gốc `comet.exe`, Agent liền kết luận ẩu icon màu trắng đó là shortcut của Perplexity Comet và xóa folder rác 1.82GB.
2. **Hậu quả:** Sau khi xóa, trên Taskbar icon màu trắng VẪN CÒN NGUYÊN!
3. **Thực tế hiện trường:** Icon màu trắng xám đó là **hộp thoại thông báo lỗi hệ thống Win32 (`#32770 System Error`)** đang hoạt động (`chrome.exe - System Error` do GPMLogin gọi thiếu file `chrome_elf.dll`). Vì GPMLogin đang chạy toàn màn hình (fullscreen/maximized) nên popup lỗi bị che khuất ở phía sau. Khi click vào icon trên Taskbar, Windows chỉ chớp focus vào popup lỗi bị che chứ không mở ứng dụng mới, tạo cảm giác "bấm vào không mở lên được". Trên Windows 10, các popup lỗi hệ thống `#32770` không có icon riêng nên Windows tự gán **biểu tượng khung cửa sổ màu trắng xám (generic window icon)**.

---

## 2. Quy Trình Triage Chuẩn (Windows Taskbar Mystery Icon Protocol)

Khi người dùng hỏi về icon lạ, icon màu trắng, icon lỗi hoặc app bấm không mở trên thanh Taskbar:

### Bước 1: Phân Định Tuyệt Đối: Pinned Shortcut vs Active Running Window
CẤM đoán mò icon đó là shortcut pinned trước khi kiểm tra các cửa sổ đang chạy!
- **Pinned Shortcut (Ghim tĩnh):** Không có vạch xanh/gạch chân active bên dưới. Nằm cố định ở đầu taskbar.
- **Active Window (Cửa sổ đang chạy):** Có gạch chân highlight/active bên dưới hoặc khung sáng khi rê chuột. Có thể là một tiến trình chạy ngầm, một app bị treo, hoặc một hộp thoại lỗi modal.

### Bước 2: Liệt Kê Các Cửa Sổ Taskbar Đang Sống (Win32 EnumWindows)
Dùng script Python gọi Win32 API lọc ra chính xác các cửa sổ xuất hiện trên thanh Taskbar:

```python
import win32gui, win32process, win32con, psutil

def get_taskbar_windows():
    results = []
    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        is_tool = bool(ex_style & win32con.WS_EX_TOOLWINDOW)
        is_app = bool(ex_style & win32con.WS_EX_APPWINDOW)
        
        # Tiêu chuẩn một cửa sổ xuất hiện trên taskbar của Windows:
        if (owner == 0 and not is_tool) or is_app:
            title = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                pname = psutil.Process(pid).name()
            except Exception:
                pname = ""
            results.append({"hwnd": hwnd, "title": title, "class": cls, "rect": rect, "pname": pname, "pid": pid})
    win32gui.EnumWindows(enum_cb, None)
    return results
```

### Bước 3: Nhận Diện Bẫy Popup Lỗi Bị Che Khuất (`#32770`, `WerFault`)
- Kiểm tra các cửa sổ có class `#32770` (Dialog chuẩn của Windows), title chứa `System Error`, `Error`, `Crash`, `Warning`, hoặc tiến trình `csrss.exe` / `WerFault.exe`.
- Kiểm tra tọa độ `rect`: Nếu một ứng dụng lớn (như GPMLogin, Chrome, Game) đang chiếm full màn hình `(-8, -8, 1928, 1048)`, thì bất kỳ popup nào có kích thước nhỏ nằm ở giữa màn hình (ví dụ: `(755, 462, 1181, 641)`) sẽ rất dễ bị chìm ở dưới (Z-order) hoặc bị che khuất nếu user bấm sang ứng dụng khác.
- Đọc nội dung text bên trong dialog (`EnumChildWindows` tìm static control) để lấy nguyên văn thông báo lỗi.

### Bước 4: Soi Mắt Đối Chiếu Trực Diện (Vision Gate)
- Chụp ảnh cropped vùng taskbar và zoom to để nhìn rõ từng slot icon từ trái qua phải.
- Chụp vùng màn hình chứa popup lỗi (nếu có).
- Vẽ viền đỏ và mũi tên liên kết giữa popup lỗi và icon trên taskbar gửi cho User nghiệm thu, giải thích rõ nguyên nhân vì sao bấm không lên.
