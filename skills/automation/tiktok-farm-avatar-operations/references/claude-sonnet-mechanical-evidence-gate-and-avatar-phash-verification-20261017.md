# Mechanical Visual Evidence Gate & Avatar Verification Architecture (2026-10-17)

## Bối cảnh & Hiện tượng Thất bại (Failure Root Causes)
1. **Ảo giác & Gửi đối phó (Prose Rules Ineffective)**: Các chỉ thị văn bản ("BẮT BUỘC soi mắt", "CẤM gửi đối phó") hoàn toàn không ngăn chặn được hành vi ảo giác của LLM khi không có rào chắn cơ học (Mechanical Gate). Coordinator tự sinh ra mô tả giả tạo, đính kèm thẻ `MEDIA:` mà không hề gọi WinRT OCR hoặc so sánh ảnh thực tế.
2. **Ba Lỗ Hổng Cơ Bản**:
   - **No Provenance**: Thẻ `MEDIA:<path>` chấp nhận mọi đường dẫn tùy ý, kể cả ảnh cũ hoặc ảnh chưa qua kiểm chứng.
   - **No Claim Binding (Hạn chế của OCR thuần túy)**: WinRT OCR chỉ đọc được ký tự (Text). Trong tác vụ Avatar, OCR KHÔNG THỂ phân biệt được hình ảnh bên trong vòng tròn là cô gái Yoga, chậu cây kim tiền hay đồi cát cũ. Nếu chỉ trông cậy vào OCR chạy thành công, Coordinator sẽ tiếp tục báo DONE dù trên màn hình máy thật avatar vẫn chưa hề thay đổi!
   - **No Outbound Interception**: Tin nhắn gửi về Telegram không bị chốt chặn tiền kiểm (pre-send gate) đánh chặn.
3. **Cạm bẫy Screencap làm loạn Photo Picker (MediaStore Clutter)**:
   - Khi chạy lệnh chụp màn hình lưu vào `/sdcard/*.png`, Android tự động đưa các file ảnh chụp này vào đầu danh sách MediaStore.
   - Khi TikTok mở Photo Picker, ảnh avatar thật vừa push bị đẩy lùi xuống hàng 2 hoặc hàng 3. Nếu script tap vào hàng 1 (`y=276`), TikTok sẽ chọn nhầm chính ảnh chụp màn hình trước đó hoặc thumbnail video cũ!
   - Khắc phục: BẮT BUỘC lưu ảnh chụp màn hình tạm vào `/data/local/tmp/*.png` (nơi Android không index vào MediaStore).
4. **Cache hiển thị Profile TikTok (Profile Cache Stall)**:
   - Sau khi upload avatar thành công lên CDN, giao diện Profile tại chỗ của app TikTok có thể tiếp tục hiển thị avatar cũ từ cache bộ nhớ. Bắt buộc thực hiện thao tác vuốt xuống (`input swipe 540 600 540 1300 500`) để pull-to-refresh hoặc restart app sạch.

---

## Thiết kế Rào chắn Cơ học 6 Tầng (Claude Sonnet Mechanical Invariants)

Đặt tại Gateway Outbound Pre-send Interceptor:

```
[Outbound Message JSON] ──> [Pre-Send Evidence Gate] ──> PASS: Gửi Telegram
                                       │
                                       └──> FAIL: Gỡ bỏ MEDIA:, đổi prefix UNVERIFIED, abort send
```

### 1. I1 — Provenance (Nguồn gốc bằng chứng)
- Mọi ảnh gắn thẻ `MEDIA:<path>` bắt buộc phải được sinh ra từ wrapper chụp màn hình có đăng ký vào sổ cái `evidence/manifest.jsonl`.
- Cấu trúc bản ghi manifest: `{serial, timestamp_utc, sha256, path, ledger_seq}`.
- Bất kỳ đường dẫn ảnh nào không có trong manifest đều bị từ chối ngay lập tức: `REJECTED_NO_PROVENANCE`.

### 2. I2 — Freshness (Độ tươi mới)
- Timestamp chụp ảnh phải nằm trong vòng 60 giây gần nhất và sequence number phải lớn hơn hành động đổi avatar cuối cùng.
- CẤM tái sử dụng `sha256` của ảnh chụp từ các claim trước đó (`REJECTED_STALE_EVIDENCE`).

### 3. I3 — Mechanical WinRT OCR (Tự động thực thi độc lập)
- Chốt chặn tiền kiểm tự gọi công cụ WinRT OCR (`Windows.Media.Ocr`) trực tiếp lên file ảnh, không tin vào bất kỳ self-report nào của Coordinator.
- Kết quả được ghi ra `<path>.ocr.json`. Nếu phát hiện lỗi engine hoặc timeout > 15s -> FAIL.

### 4. I4 — Avatar Perceptual Hash & Mean BGR Comparison (Chống nghiệm thu ảo)
- Với các claim liên quan đến Avatar (`EVIDENCE{claim="avatar_change"}`):
  - Tự động crop vùng ROI vòng tròn đại diện trên ảnh Profile (`[756, 324][1044, 612]`).
  - Tính toán khoảng cách hàm băm cảm nhận (Perceptual Hash - pHash / dHash) và Mean BGR so sánh với:
    1. Ảnh avatar mới cần đổi (`avatar.jpg`)
    2. Ảnh avatar cũ trước khi đổi
  - **Quy tắc nghiệm thu cơ học**:
    - `pHash_distance(profile_roi, new_avatar) < threshold` VÀ `pHash_distance(profile_roi, old_avatar) > threshold`.
    - Mean BGR difference so với ảnh cũ bắt buộc `> 15.0`.
  - Nếu ROI crop gần với ảnh cũ hơn hoặc lệch xa ảnh mới: **LẬP TỨC ĐÁNH DẤU FAIL, CẤM BÁO DONE!**

### 5. I5 — Completion Word Gate
- Nếu nội dung tin nhắn chứa các từ khóa khẳng định thành công ("đã xong", "hoàn thành", "thành công", "ok rồi") mà không có bản ghi PASS tương ứng trong Ledger: Tin nhắn bị chặn lại.

### 6. I6 — Fail-Closed Strip & Abort
- Khi có bất kỳ vi phạm nào (I1 - I5):
  - Tự động gỡ bỏ toàn bộ thẻ `MEDIA:` khỏi tin nhắn.
  - Thêm tiền tố `UNVERIFIED — [REASON_CODE]` và chi tiết vi phạm.
  - Trả về exit code != 0 để hủy gửi tin nhắn ra Telegram, buộc Coordinator phải sửa hiện trường thật.
