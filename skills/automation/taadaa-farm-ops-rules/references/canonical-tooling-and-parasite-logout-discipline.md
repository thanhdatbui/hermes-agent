# Canonical Tooling & Parasite Account Logout Discipline (2026-09-25)

## 1. Bối cảnh & Lỗi Vận Hành (User Phạt: "Chứ có script sao mày còn đi viết nx")
Trong các đợt vận hành Farm (đặc biệt là Preflight Reg bù phát hiện `MACHINE_FULL_8_ACCOUNTS`), khi thiết bị chạm trần 8 nick do:
1. Lệch dữ liệu giữa máy thật và file Excel (acc đã reg ở máy này nhưng lưu nhầm ở máy khác).
2. Hoặc máy bị chiếm trần bởi nick ký sinh/nick rác từ nguồn khác.

**Lỗi Agent thường mắc:**
- Coordinator dispatch worker với lệnh viết lại script Python tạm từ đầu (`logout_<nick>.py`, `logout_m<N>.py`).
- Hậu quả:
  - Subagent mất 10-15 tool calls để viết code, debug selector, thiếu xử lý biên (như atx-agent port 7912, cuộn switcher, xác nhận popup).
  - Subagent bị timeout (600s) làm đứt gãy phiên làm việc.
  - Vi phạm trực tiếp chỉ đạo của User: Farm đã có sẵn bộ công cụ chuẩn hóa được test kỹ lưỡng trong `D:/Taadaa/tools/`.

---

## 2. Danh Mục Script Canonical Bắt Buộc Dùng Sẵn (Zero Re-invent)

Trước khi thực hiện bất kỳ thao tác nào, Coordinator & Worker BẮT BUỘC kiểm tra và gọi trực tiếp các script sau:

### A. Gỡ / Logout Nick Ký Sinh (Nhả trần 8 Slot TikTok)
1. **Logout đơn lẻ theo máy:**
   ```bash
   python D:/Taadaa/tools/do_logout_account.py <machine_id> <username> <serial>
   ```
   - Cơ chế: Tự động dùng `atx-agent` (port 7912) dump UI, cuộn switcher tìm đúng `<username>`, chuyển nick, vào Menu -> Cài đặt & Quyền riêng tư -> Đăng xuất -> Xác nhận popup tại `(540, 1662)`.
   - Có tự động kiểm chứng và chụp ảnh nghiệm thu `D:/Taadaa/reports/m<machine_id>_verified_logout.png`.

2. **Logout hàng loạt đối soát danh sách:**
   ```bash
   python D:/Taadaa/tools/run_logout_all.py
   ```
   - Chạy hàng loạt các máy bị phát hiện nick ký sinh theo batch an toàn.

### B. Kiểm Tra & Giám Sát Thiết Bị
- **Trích xuất hiện trường O(1) qua ADB:**
  ```bash
  python D:/Taadaa/tools/inspect_machine.py <N>
  ```
- **Kiểm tra trạng thái lock per-device:**
  ```bash
  cat C:/Users/Kibe/.codex/device-locks/machine_<N>.lock.json
  ```

### C. Dữ Liệu & Đồng Bộ Workbook
- **Đồng bộ bảng tính an toàn sang runtime farm:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"
  ```
- **Mua bổ sung Hotmail Zin OAuth2:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/tools/buy_hotmail.py --append-kibe <N> --target-machines <targets>
  ```

### D. Thẩm Định Chốt Phiên (Closeout Gate)
- **Reviewer độc lập chấm điểm:**
  ```bash
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output
  ```

---

## 3. Quy Tắc Dispatch Worker Cho Tác Vụ Thiết Bị (Action Plan)
1. **Rule #1:** CẤM dispatch goal dạng "viết script để logout". BẮT BUỘC dispatch goal dạng: "Gọi `python D:/Taadaa/tools/do_logout_account.py <M> <user> <serial>` và nghiệm thu ảnh".
2. **Rule #2:** Budget tối đa cho worker gọi script có sẵn là <= 3 tool calls, hoàn thành dưới 2 phút.
3. **Rule #3:** Luôn bọc trong Device Lock (`acquire_device_lock`) khi tác động lên thiết bị live.
