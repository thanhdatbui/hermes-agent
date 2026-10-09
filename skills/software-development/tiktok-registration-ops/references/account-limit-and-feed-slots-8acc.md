# TikTok Reg & Feed Session: Cấu hình 8 nick/máy và Nuôi feed Acc 7-8

## 1. Giới hạn Reg TikTok theo máy (Nâng từ 6 lên 8 nick/máy)
- **Ngày cập nhật:** 2026-09-06.
- **Mục đích:** Mở rộng dung lượng tài khoản tối đa trên mỗi thiết bị Android từ 6 lên 8 nick.
- **Các vị trí cấu hình trong codebase `D:/Taadaa/Tiktok_Reg`:**
  1. `D:/Taadaa/Tiktok_Reg/scripts/tiktok_target_eligibility.py`:
     - Hằng số: `MAX_ACCOUNTS_PER_MACHINE = 8`
     - Hàm `select_pending_targets(*, ..., max_accounts_per_machine: int = MAX_ACCOUNTS_PER_MACHINE)`
     - Kiểm tra điều kiện loại trừ máy: `if counts.get(stt, 0) >= max_accounts_per_machine: continue`
  2. `D:/Taadaa/Tiktok_Reg/_detect_clean.py`:
     - Tham số: `def detect_targets(..., max_accounts_per_machine: int = 8)`
     - CLI policy banner: `"Policy: source-backed + password-present + TikTok-ID-empty + max 1/STT + max 8 accs/machine"`
- **Lệnh verify syntax/bytecode sau khi sửa:**
  ```bash
  python -m py_compile _detect_clean.py scripts/tiktok_target_eligibility.py
  ```

## 2. Phân bổ ca Nuôi Feed cho Acc 7 & 8 (`D:/Taadaa/tiktok-luot nuoi acc`)
- **Phân bổ slot hiện tại:**
  - Tik1: Slot 1 - 2 (Ca sáng)
  - Tik2: Slot 3 - 4 (Ca chiều)
  - Tik3: Slot 5 - 6 (Ca tối)
  - Slot 7 & 8: 2 slot mới sinh sau khi nâng trần reg lên 8 nick/máy.
- **Khung giờ chạy cron an toàn (Tránh xung đột Farm):**
  - Giờ cấm kỵ: 01:00 (Batch reg tài khoản mới) và 04:00 (Reboot/dọn dẹp cache hệ thống).
  - Khung giờ tối ưu:
    - **Ca khuya (23:00 - 00:45):** Sau khi ca Tik3 kết thúc, trước khi batch reg 01:00 chiếm máy.
    - **Ca sáng sớm (04:30 - 06:00):** Sau khi cron 04:00 hoàn tất dọn cache, trước ca Tik1 (07:00).
- **Yêu cầu an toàn khi xây dựng cron feed acc 7-8:**
  - Luôn đi qua Device Lock (`automation-core`) để tự động skip máy đang bận.
  - Sử dụng bộ chọn tài khoản chuẩn (`account_switcher.py`) để cuộn và switch sang đúng profile tương ứng.
