# Case Study: tiktok_login_v1.py Cluster Awareness & Playwright PYTHONPATH Pollution (M261/M274)

## 1. Bối cảnh & Hiện tượng
Trong ca xử lý lỗi Farm Alert trên dàn máy Admin (M261, M274), nhiệm vụ cốt lõi là đăng nhập các tài khoản bị thiếu (`thuthanh2911` trên M261 và `khanhthu1609` trên M274) bằng script canonical `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`.

Tuy nhiên, trong quá trình thực thi đã xảy ra 4 vấn đề kỹ thuật lớn:
1. **Lỗi Trôi Trách Nhiệm (Scope Drift & Performative Canary)**: Thay vì tập trung chạy và debug trực tiếp lệnh `tiktok_login_v1.py` cho tài khoản thiếu, agent lại chạy toàn bộ flow Canary `feed-session-smoke` trên các tài khoản đã có sẵn trên máy (`chikute343`, `chicun0910`) để lấy chứng nhận "Canary Passed". User đã phản ứng gay gắt ("Mày bị nhảm lồn à? T cần fix là chạy hàm tiktok login tự nhiên cứ đi chứng minh con cặc gì v").
2. **`tiktok_login_v1.py` Bị Hardcode Đường Dẫn Cụm Kibe**:
   - Khi chạy `python tiktok_login_v1.py 261 --list`, output trả về: `Khong tim thay account nao trong tracking`.
   - Nguyên nhân: `load_tracking_accounts_for_stt()` và `resolve_device()` dùng mặc định `TRACKING_PATH` (`kibe/taikhoan_dat_v2_updated .xlsx`) và `kibe/taikhoan_run_safe.xlsx`. Cụm Admin ($STT \ge 200$) hoàn toàn không có trong các file này.
3. **Bẫy Môi Trường: `PYTHONPATH` Của Hermes Agent Làm Sập Thư Viện Playwright (`greenlet._greenlet`)**:
   - Khi `tiktok_login_v1.py` nhập xong email và TikTok chuyển sang màn hình OTP, script gọi `read_tiktok_otp_from_gpm_profile()` qua Playwright CDP để lấy mã từ Hotmail.
   - Script văng lỗi:
     ```text
     [otp-gpm] GPM OTP read error: Playwright is unavailable; install playwright
     [otp-outlook-app] Mailbox không có token Graph -> fallback mở Outlook app trên thiết bị
     STOPPED: OUTLOOK_APP_INBOX_NOT_VERIFIED
     ```
   - Nguyên nhân: Môi trường chạy có biến `PYTHONPATH` chứa các thư mục của `hermes-agent/venv/Lib/site-packages`. Trong venv này, module `greenlet._greenlet.pyd` bị lỗi biên dịch cho Python 3.12 của hệ điều hành, dẫn đến việc `from playwright.sync_api import sync_playwright` ném `ModuleNotFoundError: No module named 'greenlet._greenlet'`. Script `read_otp_gpm.py` bắt `ImportError` và gán `sync_playwright = None`, khiến nó báo sai rằng chưa cài Playwright rồi nhảy sang mở app Outlook trên điện thoại S7 làm treo máy.
4. **Bẫy Giao Diện Khi Account Dropdown Sheet Đã Mở Sẵn**:
   - Khi `open_account_dropdown()` được gọi, nếu bottom sheet "Chuyển đổi tài khoản" đã mở sẵn từ bước trước, script lại cố tìm nút chevron hoặc tên display name ở trang hồ sơ bên dưới. Do bị sheet che khuất, các thao tác tìm kiếm thất bại và ném `RuntimeError: [03_dropdown] Khong mo duoc account dropdown`.

---

## 2. Giải Pháp & Bản Vá Kỹ Thuật

### A. Kỷ luật tập trung đúng mục tiêu của User (Chống Canary Lạc Đề)
- Khi mục tiêu là fix luồng đăng nhập tài khoản thiếu: **CHẠY TRỰC TIẾP** `tiktok_login_v1.py <STT> --email <target_email> --otp-only --ss`.
- TUYỆT ĐỐI CẤM chạy Canary Feed Session trên các tài khoản khác để đối phó lấy Done Gate khi tài khoản cần đăng nhập chưa hoàn tất.

### B. Cluster-Aware Routing trong `tiktok_login_v1.py`
Trong `main()` và `resolve_device()`:
```python
def resolve_device(stt):
    ...
    from project_paths import TARGET_INVENTORY_WORKBOOK
    inv_wb = Path(r"D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx") if stt >= 200 else TARGET_INVENTORY_WORKBOOK
    from scripts.target_inventory import load_machine_devices
    dev = load_machine_devices(inv_wb).get(stt)
    if dev:
        return dev

def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    tracking_wb = TRACKING_PATH
    if args.stt >= 200:
        os.environ["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"
        os.environ["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
        admin_tracking = r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx"
        if os.path.isfile(admin_tracking):
            tracking_wb = admin_tracking
    accounts = load_tracking_accounts_for_stt(args.stt, tracking_path=tracking_wb)
```

### C. Dọn Sạch `sys.path` Trước Khi Import Playwright Trong `read_otp_gpm.py`
Trong `D:/Taadaa/Hotmail/scripts/read_otp_gpm.py`:
```python
GPM_AUTO_SRC = Path(r"D:\Taadaa\GPM auto\src")
if str(GPM_AUTO_SRC) not in sys.path:
    sys.path.insert(0, str(GPM_AUTO_SRC))

# Sanitize sys.path from hermes-agent broken venv packages
sys.path = [p for p in sys.path if "hermes-agent" not in p]

try:
    from playwright.sync_api import sync_playwright
except (ImportError, Exception):
    sync_playwright = None
```

### D. Xử Lý Account Dropdown Sheet Đã Mở Sẵn
Trong `social_reg_v1.py`:
- Trong `open_account_dropdown()`: Ngay đầu vòng lặp, kiểm tra `if _account_dropdown_open_xml(xml): log("account dropdown already open"); return True`.
- Trong `go_to_profile()`: Nếu `_account_dropdown_open_xml(cur_xml)` đã là `True`, không tap lại tab Hồ sơ để tránh đóng mất bottom sheet.
