# Parasite Account Guard & Re-Login Invariants (2026-09-23 / 2026-09-24)

## 1. NGUYÊN TẮC: GUARD CHỈ CHẶN LOGIN SAI MÁY, KHÔNG CHẶN RE-LOGIN ĐÚNG MÁY

### A. Nick bị văng ra (Session expired / Logged out):
- Khi cần login lại nick bị văng vào ĐÚNG máy của nó:
  `python tiktok_login_v1.py <stt> --email <id|email>`
- `AccountMachineBindingGuard` (`parasite_guard.py`):
  Tra cứu `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`:
  Thấy `owner_stt == target_stt` -> **ALLOW 100%**, tiến hành login bình thường.

### B. Chuyển máy có chủ đích (Migration / Máy cũ hỏng):
- Nếu máy cũ bị hỏng hoặc operator muốn chuyển nick sang máy khác:
  Bắt buộc truyền cờ `--override-machine`:
  `python tiktok_login_v1.py <new_stt> --email <id|email> --override-machine`
- Guard sẽ ghi nhận audit log `[WARN:OPERATOR_OVERRIDE]` và cho phép login sang máy mới, chống chặn nhầm thao tác hợp lệ.

### C. Ngăn chặn triệt để Nick Ký Sinh (Parasite Account):
- CẤM dùng tool reg (`social_reg_v1.py`) để login lén vào nick cũ khi TikTok báo "Bạn đã đăng ký".
- Mọi thao tác login BẮT BUỘC thực hiện qua `tiktok_login_v1.py` với kiểm tra ownership rõ ràng.
