# Invariant: Cấm Tự Viết Ad-hoc Switcher — Bắt Buộc Dùng Canonical Account Switcher Trong automation-core

## 1. Hiện tượng & Bẫy Kỹ Thuật (Anti-Pattern)
- **Tự chế loop OCR/tọa độ để switch account:**
  Khi một script cần chuyển đổi giữa các tài khoản TikTok trên thiết bị (như runner đổi tên, upload avatar, kiểm tra profile), agent thường có xu hướng xấu là tự viết vòng lặp:
  1. Dò text username bằng WinRT OCR / Tesseract.
  2. Tính tâm bounding box rồi gửi lệnh `adb shell input tap x y`.
  3. Vuốt màn hình bằng tọa độ cứng `input swipe ...`.
- **Hậu quả nghiêm trọng:**
  - **Kẹt vòng lặp vô tận (Loop Trap):** Khi tài khoản mục tiêu **đã đang active sẵn** trên Profile, việc mở Switcher ra rồi tap lại vào dòng của chính nó sẽ khiến TikTok không làm gì cả, khay Switcher vẫn mở. Script nhận nhầm là chưa switch xong, lại tap tiếp $\to$ Kẹt 30-35 lần liên tiếp $\to$ Dính circuit breaker `exit_2`.
  - **Lệch giao diện (Sticky Header Trap):** Trên TikTok layout mới (46.x / 47.x), tên tài khoản nằm lệch trái hoặc bị che, nếu không vuốt nhẹ sticky header ($y=0.65h \to 0.42h$) thì tap vào tên sẽ không mở được Account Switcher.
  - **Kẹt đáy màn hình (Navigation Guard):** Hàng tài khoản thứ 7, 8 hoặc nút *"Thêm tài khoản"* bị dồn sát đáy màn hình ($y > 1840$ trên 1080p), tap vào tâm node sẽ trúng thanh điều hướng hệ thống (Android System Navigation Bar).

---

## 2. Tiêu Chuẩn Triển Khai (Canonical Contract)
MỌI công cụ, runner, watchdog cần chuyển đổi tài khoản TikTok trên farm **BẮT BUỘC** gọi qua canonical interface của `automation-core`:

```python
import sys
sys.path.insert(0, r"D:\Taadaa\automation-core\src")
sys.path.insert(0, r"D:\Taadaa\tiktok-follow")

from follow_runner.core.adapter import FollowAdapter
from automation_core.tiktok.account_switcher import (
    open_account_switcher,
    select_exact_account,
    verify_selected_account,
    AccountSwitcherError,
)

def canonical_switch_account(adb_path: str, serial: str, target_user: str, machine_id: int) -> bool:
    adapter = FollowAdapter(adb_path, serial)
    try:
        # 1. Mở Switcher (tự động xử lý sticky header, profile root, back subpage)
        open_account_switcher(adapter, profile_attempts=3, switcher_attempts=3, load_attempts=3)
        
        # 2. Chọn đúng tài khoản (tự động cuộn viewport nếu acc nằm ở dòng 5-8, tự back nếu acc đã active)
        post_xml = select_exact_account(adapter, target_user)
        
        # 3. Thẩm định chắc chắn tài khoản đã active sau khi switch
        verify_selected_account(adapter, target_user, xml_text=post_xml)
        return True
    except AccountSwitcherError as exc:
        if exc.code == "ACCOUNT_MISSING":
            # Khi tài khoản văng khỏi khay switcher -> kích hoạt luồng khôi phục đăng nhập chuẩn
            login_cmd = [
                sys.executable,
                r"D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py",
                str(machine_id),
                "--email", target_user,
                "--ss", "--allow-parent-lock",
            ]
            res = subprocess.run(login_cmd, capture_output=True, text=True, timeout=180)
            return res.returncode == 0
        raise
```

---

## 3. Quy Tắc Vận Hành (Operational Invariants)
1. **CẤM TUYỆT ĐỐI tự viết ad-hoc switcher:** Không viết thêm bất kỳ hàm OCR/tap coordinate nào để tự mở hay chọn tài khoản trong Switcher.
2. **Kế thừa khả năng tự chữa lành (Self-Healing):** `automation_core.tiktok.account_switcher` đã có sẵn logic phục hồi ATX, reset UI hierarchy khi dump lỗi, và tự động bỏ qua nếu đã chọn đúng tài khoản.
3. **Phân biệt rõ Missing vs Switched:** Chỉ khi `select_exact_account` ném ra ngoại lệ `AccountSwitcherError` với mã `ACCOUNT_MISSING` (sau khi đã cuộn 3 lần) mới được kích hoạt `tiktok_login_v1.py`.
