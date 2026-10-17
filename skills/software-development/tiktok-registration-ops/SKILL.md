---
name: tiktok-registration-ops
description: "Vận hành batch đăng ký TikTok (reg) — detect target mail chưa reg, giành lock máy, chạy _run_all_targets.py, resume tại chỗ, debug DOB/OTP blockers."
---

# TikTok Registration Operations

## 1. Nguyên Tắc Cốt Lõi
- **Không thao tác tay:** Mọi luồng đăng ký phải chạy qua script tự động `_run_all_targets.py`.
- **Đọc OTP:** Đọc tự động qua Graph API từ PC cho Hotmail token, không login bằng app Outlook chậm chạp.
- **Xử lý ngày sinh & OTP:** Tap đúng tâm nút ngày sinh (y=1788). Nếu kẹt màn hình mã PIN lỗi -> lùi về lấy OTP mới.

## 2. Lệnh Vận Hành Canonical
- **Chạy batch đăng ký:** `python _run_all_targets.py --full-scope-takeover`
- **Resume máy kẹt:** `python social_reg_v1.py <stt> --resume --email <mail>`
- **Kiểm tra hiện trường O(1):** `python D:/Taadaa/tools/inspect_machine.py <N>`

## 3. Danh Mục Tham Khảo Chi Tiết
- Chi tiết các case study reg lỗi và xử lý màn hình: xem danh mục trong thư mục `references/` của skill.
