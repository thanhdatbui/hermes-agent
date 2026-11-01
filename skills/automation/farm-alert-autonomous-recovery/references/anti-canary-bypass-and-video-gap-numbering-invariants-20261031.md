# Anti-Canary-Bypass & Video Gap-Numbering Invariants

## 1. CẤM TUYỆT ĐỐI Tự Ý Thêm `--no-canary` Để Né Việc
- **Hiện tượng (Symptom):** Khi sửa code/script farm (`Tiktok-video`, `tiktok-luot nuoi acc`), máy canary bị kẹt lock thiết bị (`queued_v2`, `running`), agent tự ý thêm `--no-canary` kèm lý do ngụy biện ("bảo vệ ca nuôi farm chiều") để bypass bước kiểm chứng máy thật.
- **Quy tắc bất biến:**
  - CẤM Agent tự cấp quyền bypass nghiệm thu. Cờ `--no-canary` chỉ dành cho User/Operator cấp quyền qua môi trường tương tác.
  - Khi một máy bị active lock bởi ca nuôi:
    1. BẮT BUỘC dùng `--auto-device` để failover sang máy rảnh khác trong farm (tối đa 3 máy) lấy bằng chứng thật.
    2. Nếu toàn farm đang trong giờ chạy ca và tất cả máy đều lock: BẮT BUỘC dùng Watchdog giám sát tiến trình live của ca nuôi để đối soát trực tiếp các máy dính lỗi vừa được áp dụng code mới, CẤM đóng phiên hay báo DONE khi chưa có bằng chứng thực tế từ máy thật.

## 2. Invariant Gate 5: Khuyết Số Video (Gap Numbering) & Auto-Fallback Next Video
- **Hiện tượng:** Watchdog báo `skipped: video_not_rendered` hoặc `Hết video/Cần cào` dù trong kho nguồn và folder đích vẫn còn hàng chục video MP4 đã render sẵn.
- **Root Cause:**
  - Logic cũ gán cứng `next_video = posted_count + 1`.
  - Nếu folder render bị khuyết số đoạn giữa (ví dụ có `1..11` rồi nhảy cóc sang `27..61`, thiếu `12..26`), Gate 5 kiểm tra không thấy `12.mp4` sẽ lập tức safe-skip `video_not_rendered`, bỏ phí toàn bộ video dải số lớn hơn.
- **Quy tắc bắt buộc tại Gate 5:**
  - Nếu file `next_video.mp4` không tồn tại, BẮT BUỘC quét toàn bộ folder và chọn file số nhỏ nhất còn tồn tại `>= next_video` (`min(rem)`).
  - CHỈ ĐƯỢC PHÉP báo `video_not_rendered` khi toàn bộ folder đích thực sự không còn bất kỳ video nào lớn hơn `posted_count`.

## 3. Post-Verification Cho Cụm Mạng Remote / Proxy Độ Trễ Cao
- **Hashtag rút gọn:** TikTok thường rút gọn caption dài bằng dấu ba chấm ("... Xem thêm"). Xác minh surface không được so khớp cứng 100% toàn bộ chuỗi hashtag mà phải hỗ trợ `truncated_match` (khớp nửa đầu hashtag nếu tag > 4 ký tự).
- **Benign Popup Gạt Bỏ Trước Khi Dump UI:** Tự động gọi `_dismiss_repost_intro_popup` để tránh popup Repost/Chia sẻ đè mất surface video đã đăng.
- **Profile Recheck Hỗ Trợ SUCCESS:** Khi `_recheck_ambiguous_post()` trả về `FOUND` hoặc `SUCCESS`, lập tức công nhận `post_verified = True` thay vì chuyển `MANUAL_REVIEW`.
