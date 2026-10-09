# Fill Email Timeout Fallback Contract (social_reg_v1.py)

## Vấn đề
Khi đăng ký TikTok bằng `social_reg_v1.py`, tại bước `fill_email_and_next()`, script điền email và ấn nút "Tiếp tục". Nếu mạng chậm/lag khiến UI không load kịp sang màn hình OTP hoặc form đăng ký mới:
- Script fallback sang `unknown_fallback` sau khi chờ.
- Trước đây, nhánh fallback này ghi log `khong xac dinh, thu tiep theo` và `continue`.
- Khi hết danh sách candidates, script mặc định kết luận:
  `RuntimeError: [07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok`
- Đây là kết luận sai (false positive), gây nhầm lẫn là email đã đăng ký rồi trong khi thực tế chỉ là do mạng timeout không load kịp.

## Patch Contract chuẩn
1. **Contract 1**: Khởi tạo cờ lỗi `had_timeout_error = False` trước vòng lặp duyệt candidates cùng với `had_network_error` và `had_form_error`.
2. **Contract 2**: Tại nhánh fallback unknown sau timeout, set `had_timeout_error = True` và log rõ `khong xac dinh (timeout loading), thu tiep theo`.
3. **Contract 3**: Cuối vòng lặp, kiểm tra `had_timeout_error` trước khi raise lỗi "đã có TK":
   ```python
   if had_timeout_error:
       raise RuntimeError(f"[07] Khong the xac dinh trang thai email cho STT {stt} do timeout/mang cham khi bam Tiep tuc ('{em}')")
   raise RuntimeError(f"[07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok")
   ```
