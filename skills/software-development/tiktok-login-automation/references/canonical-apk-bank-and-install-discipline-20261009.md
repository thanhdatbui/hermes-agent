# Canonical APK-Bank & Farm APK Installation Discipline (Taadaa Phone Farm)

## BỐI CẢNH & PHẢN HỒI NGƯỜI DÙNG (09/10/2026)
User bức xúc và chấn chỉnh nghiêm khắc khi agent tự ý mò vào thư mục con và viết script push từng split APK:
> *"trong thư mục apk bank đã có đầy đủ thành phần r, t đéo hiểu sao lần lồn nào cập nhật cũng bị thieeus file..."*

---

## 1. NGUYÊN TẮC BẤT BIẾN KHI CÀI ĐẶT / CẬP NHẬT APK TRÊN FARM

### 1.1. CẤM TỰ VIẾT SCRIPT PUSH / CÀI APK THỦ CÔNG
- **CẤM TUYỆT ĐỐI**: Tự viết script Python `adb push`, `pm install`, `pm install-create/write/commit` ad-hoc để cài app.
- **BẮT BUỘC DÙNG TOOL CANONICAL DUY NHẤT**:
  `D:/Taadaa/tools/install_farm_apks.py`
  Tool đã được tối ưu hóa:
  - Tự động nhận diện thiết bị (qua STT hoặc Serial).
  - Tự động nạp đúng bộ file APK chuẩn từ `D:\OneDrive\apk-bank`.
  - Hỗ trợ cờ `--force` để cài đè (reinstall an toàn giữ data).
  - Hỗ trợ cài đa luồng `--workers`.

### 1.2. NGUYÊN TẮC TIÊU HỦY NGAY THƯ MỤC / ARTIFACT HỎNG (CHỐNG CỐ ĐẤM ĂN XÔI)
- Khi phát hiện một thư mục APK hỏng/phân mảnh (ví dụ `v47.0.3` bị chia 65 split files thiếu Dex classes gây crash `NoClassDefFoundError`), file tải dở hoặc artifact lỗi:
  **BẮT BUỘC TIÊU HỦY XÓA BỎ NGAY LẬP TỨC** (`rm -rf` / `shutil.rmtree`).
- **TUYỆT ĐỐI CẤM**: Giữ lại thư mục rác để thử cài đi cài lại hay chắp vá file. Việc giữ thư mục hỏng làm ô nhiễm kho `apk-bank` và khiến các lượt chạy sau/watchdog tiếp tục vấp ngã.
- Phản hồi từ User: *"vkl mày, thư mục lỗi thì mày xoá con mẹ nó đi"*.

### 1.3. XỬ LÝ SỰ CỐ VERSION DOWNGRADE TRÊN THIẾT BỊ
- Khi thiết bị lỡ bị cài phiên bản cao hơn (như v47.0.3) và cần quay về bản chuẩn farm (v46.6.3), lệnh `install -r` sẽ bị chặn bởi `Failure [INSTALL_FAILED_VERSION_DOWNGRADE]`.
- **BẪY `pm uninstall -k` (GIỮ DATA):** Tuyệt đối KHÔNG dùng `pm uninstall -k` hoặc `cmd package uninstall -k`. Lệnh này giữ lại thư mục `/data/data` và bản ghi package trong `/data/system/packages.xml`, do đó hệ điều hành Android vẫn lưu mốc version code cao hơn và TIẾP TỤC chặn hạ cấp bằng `INSTALL_FAILED_VERSION_DOWNGRADE`.
- **Quy trình chuẩn gỡ sạch & cài lại 55 Split APKs:**
  1. Gỡ bỏ triệt để (xóa sạch metadata package):
     ```bash
     adb shell pm clear com.ss.android.ugc.trill
     adb uninstall com.ss.android.ugc.trill
     ```
  2. **Kỹ thuật cài đặt Split APK qua Local Shell (chống nghẽn socket ADB remote):**
     Khi truyền 55 file split qua mạng ADB từ xa (Remote ADB Host `192.168.110.119:5037`), việc stream trực tiếp bằng `install-multiple` rất dễ bị `TimeoutExpired` hoặc đứt session giữa chừng.
     Giải pháp chuẩn 100%:
     - Đẩy toàn bộ split APK vào bộ nhớ đệm thiết bị: `/data/local/tmp/trill_m267/*.apk`
     - Chạy script install session trực tiếp trên shell Android:
       ```bash
       # 1. Tạo session
       session_id=$(adb shell cmd package install-create -r | grep -oE '[0-9]+')
       # 2. Ghi từng split APK vào session (dùng stat để lấy size chính xác)
       adb shell "for f in /data/local/tmp/trill_m267/*.apk; do
           sz=\$(stat -c %s \"\$f\")
           name=\$(basename \"\$f\")
           pm install-write -S \$sz $session_id \"\$name\" \"\$f\"
       done
       pm install-commit $session_id"
       ```
     - Thời gian cài đặt cục bộ trên máy S7 chỉ tốn ~40–60 giây, ổn định tuyệt đối và tránh nghẽn băng thông ADB.
  3. Khởi động app vượt màn hình onboarding ban đầu ("Chọn sở thích") về trang chủ.
  4. Chạy lại script login chuẩn (`tiktok_login_v1.py`) để nạp lại tài khoản an toàn từ Graph API OAuth2.

### 1.2. KHO APK CHUẨN FARM (`D:\OneDrive\apk-bank`)
Tuyệt đối không tự ý chui vào các thư mục con phân mảnh (ví dụ `com_ss_android_ugc_trill/v47.0.3` có 65 dynamic feature splits thiếu class Dex gây `NoClassDefFoundError`).
Kho chuẩn farm nằm tại:
- **TikTok (Split APK 3 file chuẩn)**:
  `D:\OneDrive\apk-bank\com_ss_android_ugc_trill\`
  - `base.apk`
  - `split_config.arm64_v8a.apk`
  - `split_config.vi.apk`
- **Outlook**:
  `D:\OneDrive\apk-bank\com_microsoft_office_outlook\`
- **ViChanger**:
  `D:\OneDrive\apk-bank\vn_vichanger_app\base.apk`

### 1.3. INVARIANT REMOTE ADB CHO CỤM ADMIN (201–280)
Mọi lệnh gọi `install_farm_apks.py` hoặc CLI ADB tương tác với dàn Admin BẮT BUỘC nạp socket:
```bash
ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" python D:/Taadaa/tools/install_farm_apks.py --device <serial> --apps trill --force
```
Nếu thiếu `ADB_SERVER_SOCKET`, ADB mặc định kết nối `localhost:5037` và lập tức báo `device not found`.

---

## 2. QUY TẮC MỞ ACCOUNT SWITCHER TRÊN GIAO DIỆN TIKTOK MỚI

### 2.1. Phản hồi chuẩn hóa từ User:
> *"Vuốt xuống ở trang profile cho id nó nằm trên cùng chính giữa xong ms bấm vào nó ms bung account switcher ra r ms bấm thêm tài khoản chứ?????"*

### 2.2. Cơ chế thực tế:
- Trên UI TikTok mới, tên người dùng ở trạng thái tĩnh nằm lệch bên trái và **KHÔNG CÓ nút mũi tên ▼**. Bấm vào tên tĩnh sẽ bị hiểu nhầm là bấm vào widget gắn vị trí/chủ đề cá nhân.
- **Thao tác chuẩn**:
  1. Thực hiện vuốt nhẹ trang Profile từ dưới lên (swipe up, ví dụ `540, 1200 -> 540, 600`) để thanh tiêu đề dính (sticky top header bar `pmi`/`pmf`) trượt lên cố định ở **TRÊN CÙNG CHÍNH GIỮA** màn hình.
  2. Bấm vào tiêu đề ở chính giữa (`x=540, y=150`) để bung Account Switcher trượt từ đáy lên.
  3. Bấm "Thêm tài khoản" hoặc chọn tài khoản cần chuyển.
