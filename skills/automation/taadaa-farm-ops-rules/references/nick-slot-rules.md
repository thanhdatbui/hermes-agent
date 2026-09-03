# Nick Slot Mapping & Device Swap Rules

## Nick Slot Structure (Kibe 1-80)
- **480 slot chuẩn**: 80 máy × 6 nick/máy (`taikhoan_run_safe`)
- **3 Ca / Ngày**:
  - Ca 1 (Sáng): Row 1, 2
  - Ca 2 (Chiều): Row 3, 4
  - Ca 3 (Tối): Row 5, 6 (Phiên 3 up video: #1 auto-ava, #2+ skip)

## Account Limits
- **Max 6 acc/máy** (1 per row)
- **Nick ≥ 5 video**: Follow 15-20/phiên (max 60/ngày), 0 video cấm follow
- **Lock**: 90 phút
- **Feed**: max 40w, up sem 20, follow timeout 1200s

## Swap Rule (QUAN TRỌNG)
- **Chỉ swap khi máy full 6 nick**
- **Thiếu nick**: BẮT BUỘC chạy `reconcile_tiktok_accounts.py` để fill
- **CẤM TUYỆT ĐỐI**: tự đôn slot / chuyển nick sang máy khác

## Delete Dead TT Account
- Xóa trong `taikhoandatv2`
- **Trong gmail_clean_v2: BẮT BUỘC GHIỮ mail và đánh dấu status** (`die/banned/khoa/used`) để script không chọn lại

## Account Profile Entropy
Dùng `account-profile-entropy` skill để gen profile VN thực tế (tên, username, DOB, phone, device fingerprint).