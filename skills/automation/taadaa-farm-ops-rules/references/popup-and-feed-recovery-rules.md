# Popup & Feed Auto-Recovery Rules (Taadaa Farm - 21/08/2026)

## 1. Quảng cáo & Overlay tương tác (Ad Overlay / Sponsored Cards)
- **Quy tắc cốt lõi:** Mọi màn hình quảng cáo, ad overlay, sponsored card -> **BẮT BUỘC VUỐT LÊN (swipe up: `input swipe 540 1600 540 400 300`)** để chuyển sang video tiếp theo.
- **Nút Đóng/Hủy:** CHỈ là fallback cuối cùng khi đã vuốt 2 lần mà màn hình vẫn bị kẹt lại. Tuyệt đối cấm viết handler chỉ tap nút Đóng làm luồng chính.

## 2. Popup 'Follow bạn bè của bạn' (Follow lại / Follow Back)
- **Quy tắc cốt lõi:** Khi gặp modal popup gợi ý bạn bè có các nút **'Follow lại' / 'Follow back'**, **BẮT BUỘC BẤM TOÀN BỘ NÚT 'Follow lại'** để tận dụng tăng follow chéo tự nhiên cho tài khoản farm.
- **Giải phóng modal:** Sau khi tap follow lại, tìm nút X đóng popup (hoặc gửi phím Back) để quay lại For You Feed tiếp tục nuôi tài khoản.

## 3. Cơ chế cứu hộ màn hình lạ / Popup chưa rõ (Unhandled Popup Swipe Recovery)
- **Quy tắc 2 lần vuốt:** Gặp bất kỳ popup lạ hoặc màn hình không nằm trong allowlist, script phải gọi `_swipe_recovery_on_stuck` thử vuốt lên 2 lần để thoát tự động trước khi gửi alert hay dừng phiên.
- **Không chặn vuốt:** Tuyệt đối không chặn nhánh vuốt cứu hộ bằng điều kiện `after_attempt is None`.

## 4. Reset & Clean Bytecode (__pycache__)
- Khi deploy bản sửa code cho farm runner chạy song song nhiều worker, bắt buộc dọn sạch file `.pyc` (`find ... -name "*.pyc" -delete`) để tránh worker chạy lại bytecode cũ đã biên dịch từ trước.
