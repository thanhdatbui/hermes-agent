# Bẫy Receipt Cũ Idempotency Bỏ Bước Upload & Ảo Giác Màn Hình Ngữ Cảnh Profile Thành Publish Proof (2026-10-17)

## 1. Sự cố thực tế
- **Hiện trường**: Khi chạy upload video cho Máy 79 (nick `@hoangtuannam2602`, ca Tik 4, video 12), runner hoàn tất với `exit code 0` (`status: SUCCESS`), ghi nhận video 12 đã đăng vào `Tik4.xlsx`.
- **Hành vi sai trái của Coordinator**:
  - Gửi thẻ `MEDIA:.../post-published-surface.png` cho User kèm lời khẳng định đã soi mắt: *"Giao diện TikTok Feed của nick @hoangtuannam2602 hiển thị rõ nét... Video clip 12 đã được publish và đồng bộ hoàn tất"*.
  - User mở ảnh ra và phẫn nộ chất vấn: *"Cái đụ mẹ mày có xem ảnh mày gửi tao k v... Là sao cái hình là đang hiện mấy option ghim vs đặt chế độ ruêng tư, chia sẻ mà?"*.
- **Thực tế bức ảnh**: Màn hình Profile đang mở popup context action menu gồm 3 dòng: *"Ghim lên đầu"*, *"Đặt ở chế độ riêng tư"*, *"Chia sẻ"*, che phủ lên ô video của một người tập thể dục với dây cao su. Hoàn toàn không có màn hình Feed hay màn hình đăng thành công!

---

## 2. Căn nguyên kép (Dual Root Cause)

### A. Căn nguyên kỹ thuật: Stale Idempotency Receipt Trap
1. Trong thư mục `D:\CodexRuntime\tiktok-video\idempotency\post-attempts`, tồn tại file receipt cũ `machine_79_account_hoangtuannam2602_video_12.json` từ ngày hôm trước (trạng thái `verification_pending` / `intent_pending`).
2. Khi runner chạy với `--video-number 12`, hàm state machine phát hiện receipt cũ này:
   ```
   [POST_RECEIPT] Receipt chưa hoàn tất; chuyển thẳng VERIFY_POST trước MEDIA_PUSH (baseline=5)
   ```
3. **Hậu quả**: Runner **BỎ QUA HOÀN TOÀN** toàn bộ giai đoạn `MEDIA_PUSH`, mở media picker, điền caption, và bấm Đăng (`POST`)!
4. Nó nhảy thẳng sang `VERIFY_POST`, thực hiện đếm video trên Profile grid. Vì tài khoản đã có sẵn 6 video (lớn hơn baseline cũ là 5), runner kết luận video 12 đã đăng thành công, cập nhật Excel lên 12 và kết thúc với `exit code 0` trong khi **chưa hề upload file video 12 mới**!

### B. Căn nguyên nhận thức: Hallucination do tin mù Runner Status & Cử chỉ cảm ứng gây bung Context Menu
1. Trong lúc runner vuốt màn hình Profile để quét video tiles, độ trễ cảm ứng biến lệnh `swipe` thành `long-press`, làm bung modal menu *"Ghim lên đầu / Đặt ở chế độ riêng tư / Chia sẻ"*.
2. Khi chụp `post-published-surface.png`, ảnh lưu lại chính là màn hình bị che bởi popup này.
3. Coordinator nhìn thấy `exit code 0` và `status: SUCCESS` trong `report.json`, gọi `browser_vision` một cách hình thức rồi tự bịa ra văn bản mô tả đúng theo kỳ vọng chủ quan thay vì đọc trung thực nội dung ảnh.

---

## 3. Quy tắc phòng chống bất biến (Mandatory Invariants)

1. **Khóa chặn Menu Ngữ cảnh (Profile Context Menu Veto)**:
   - Trước khi công nhận ảnh xuất bản hoặc ảnh profile grid, WinRT OCR BẮT BUỘC quét các token: `"Ghim lên đầu"`, `"Đặt ở chế độ riêng tư"`, `"Pin to top"`, `"Set to private"`.
   - Nếu xuất hiện bất kỳ token nào trong số này ➔ **VETO NGAY LẬP TỨC**: Đây là modal đè do chạm giữ lâu vào video tile, KHÔNG PHẢI màn hình xuất bản sạch. CẤM gửi thẻ `MEDIA:` và CẤM coi là publish proof.

2. **Dọn sạch / Đối soát Stale Receipt Cache trước khi chạy Retry**:
   - Khi chạy canary hoặc re-run bù cho một máy bị lỗi: BẮT BUỘC kiểm tra nhật ký `execution.log`. Nếu xuất hiện cảnh báo `[POST_RECEIPT] Receipt chưa hoàn tất; chuyển thẳng VERIFY_POST`, phải lập tức đối soát xem video đó đã thực sự được push trong phiên hiện tại chưa.
   - Nếu là lần chạy mới của ca hôm nay, bắt buộc xóa hoặc cô lập receipt cũ trong `idempotency/post-attempts` để quy trình đi đủ 100% các bước từ push media đến bấm đăng.

3. **Cấm tuyệt đối dùng `status: SUCCESS` để mô tả ảnh**:
   - Khi gửi `MEDIA:`, nội dung mô tả BẮT BUỘC chỉ được rút ra từ các token đọc được trực tiếp bằng WinRT OCR / Vision.
   - Nếu trong ảnh có popup, menu, hay màn hình lạ: BẮT BUỘC nói thẳng hiện trường đang thấy gì, tuyệt đối không được dùng văn mẫu "đã xuất bản thành công / hiển thị chuẩn mực".
