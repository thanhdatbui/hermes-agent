# Excel Preflight Validator & Dual-Cluster Farm Invariants (Kibe & Admin)

Phiên làm việc: 17/09/2026.
Bối cảnh: Phát hiện chuỗi lỗi lặp đi lặp lại trên Farm: Nick chính chủ bị văng Switcher do reg/bù đè không kiểm tra Switcher máy thật; Excel gõ trùng Video Gốc (Tik3); lệch slot và duplicate slot 7 sang slot 8; gõ nhầm mật khẩu vào ô Folder Video.

## 1. Bản chất gốc rễ (Root Cause)
- **Write-Without-Read**: Code tự động ghi vào Excel / cấu hình runtime mà không đối soát trạng thái thực tế của máy trước khi hành động.
- **Triple-Write Mất Đồng Bộ**: Dữ liệu nằm ở 3 nơi (Excel, SQLite state.db, Thiết bị thật) không có atomic sync.
- **Excel Thiếu Schema Validation / Unique Constraint**: Người điều hành kéo copy lệch dòng hoặc gõ nhầm giá trị nhưng không có lớp kiểm tra chặn trước.

## 2. Thiết kế giải pháp: Pragmatic Hybrid Architecture (Hội đồng Kỹ thuật Ký Duyệt)
- **Không bỏ Excel**: Excel vẫn là giao diện nhập liệu trực quan cho người điều hành.
- **Preflight Gate Fail-Fast**: Mọi pipeline runtime trước khi đồng bộ dữ liệu vào bot BẮT BUỘC phải đi qua `excel_preflight_validator.py`.
- **Chặn đứng khi vi phạm**: Nếu phát hiện vi phạm 1 trong 5 Invariant Rules, hủy ngay đồng bộ sang runtime để bảo vệ Farm.

## 3. 5 Invariant Rules Bắt Buộc
1. **Rule 1 (Slot Limit per Machine)**: Mỗi máy tối đa 8 tài khoản. Không xuất hiện trùng lặp máy trong cùng 1 file Tik.
2. **Rule 2 (No Duplicate Accounts)**: Tài khoản là độc bản toàn farm, không xuất hiện ở 2 slot khác nhau trong cùng file hoặc giữa các file `Tik1..Tik8.xlsx`.
3. **Rule 4 (Folder Video Formula & Uniqueness)**: Folder Video độc bản toàn farm, khớp công thức chuẩn:
   - Cụm Kibe (`M1..M80`, offset = 0): `(m - 1) * 8 + slot`.
   - Cụm Admin (`M201..M280`, offset = 200, $m' = m - 200$): `(m' - 1) * 8 + slot`.
4. **Rule 4 (Video Gốc Formula & Uniqueness)**: Video Gốc độc bản trong cùng 1 file Tik{slot}.xlsx (không 2 máy nào trong cùng 1 ca dùng chung video gốc), khớp công thức:
   - Cụm Kibe: `(slot - 1) * 80 + m`.
   - Cụm Admin: `(slot - 1) * 80 + m'`.
5. **Rule 5 (taikhoan_run_safe.xlsx Invariants)**: Mỗi máy tối đa 8 dòng, serial phần cứng không được rỗng, tài khoản không trùng lặp giữa các máy khác nhau.

## 4. Tích hợp thực tế vào Pipeline Farm
- Script thực thi: `D:/Taadaa/tools/excel_preflight_validator.py`.
- Bộ test suite: `D:/Taadaa/tools/test_excel_preflight_validator.py` (Unit tests 6/6 PASS).
- Điểm chèn cổng chặn: `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_taikhoan_sync_cron.py` (Bước 2b trước khi `generate_cron_source_config`).
