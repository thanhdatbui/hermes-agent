# Quy tắc Điều phối & Vận hành Lịch 4 Ca x 2 Phiên / Ngày (User chốt 11-12/09/2026)

## 1. Cơ chế Upload Video linh hoạt ở CẢ Phiên 1 & Phiên 2 (Tối đa 1 lần / ca)
- **Trước đây:** Chỉ mở upload hook ở Phiên 2 (`session_index == 2`). Nếu Phiên 2 dính lỗi thì mất trắng cơ hội đăng video của cả ca.
- **Quy tắc mới:** Cả Phiên 1 và Phiên 2 đều được kích hoạt `--allow-upload-hook`.
  - **Phiên 1:** Sau khi lướt feed, kiểm tra nếu có video theo Row trong ca thì tiến hành đăng luôn.
  - **Phiên 2:** 
    - Nếu Phiên 1 **đã đăng thành công**: `_ShiftUploadLedger` kiểm tra thấy đã có bản ghi `status: success` $\rightarrow$ Safe-Skip ngay lập tức trong 0.1s (`reason: already_uploaded_in_shift`).
    - Nếu Phiên 1 **chưa đăng / không có video / bị lỗi**: Phiên 2 tự động đăng bù.
- **Cam kết an toàn:** Khóa nguyên tử `_ShiftUploadLedger` bảo đảm mỗi máy/tài khoản **chỉ đăng tối đa 1 video / ca**. Hoàn toàn không xảy ra tình trạng đăng 2 lần.

---

## 2. Cơ chế Follow Hook thống nhất theo Ngưỡng Tối thiểu 5 Video (Case 151)
- **Gỡ bỏ hoàn toàn việc chặn cứng theo Row:** Bỏ rule cũ `if row_idx in (3, 4, 5, 6): return skipped "tik{row}-warmup-feed-only"`.
- **Áp dụng 1 điều kiện duy nhất cho tất cả các Row (1..8):**
  - Nick có **tối thiểu 5 video (`video_count >= 5`)** mới được kích hoạt follow hook.
  - Nick $< 5$ video (0..4 video hoặc rỗng) tự động safe-skip (`under-5-videos-follow-disabled`) để tránh bị TikTok nghi ngờ nick rác và nhả follow.

---

## 3. Kỷ luật Báo cáo Chốt phiên (Mandatory Report Discipline)
- Khi user yêu cầu "chốt phiên", báo cáo BẮT BUỘC phải tóm tắt đầy đủ cả **3 trụ cột vận hành**:
  1. **Lướt Feed:** Số lượng máy thành công, tỷ lệ hoàn thành.
  2. **Đăng Video (Upload Hook):** Đã đăng bao nhiêu video, phiên nào đã xử lý, cơ chế bù phiên ra sao.
  3. **Follow Chéo (Follow Hook):** Tình trạng follow, số lượt follow hoàn thành, các máy bị nhả follow theo đúng 4 nhóm chuẩn.
- Tuyệt đối không được bỏ quên Follow hook trong báo cáo tổng kết.
