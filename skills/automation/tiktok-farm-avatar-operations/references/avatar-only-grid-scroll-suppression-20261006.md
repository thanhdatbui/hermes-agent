# Bẫy Cuộn Đếm Lưới Video Profile trong Avatar-Only Gây Kẹt Feed & Văng Profile Root (06/10/2026)

## Bối cảnh sự cố
Khi chạy đổi avatar cho tài khoản `@hatien15118` trên Máy 11 Tik 1 (`run_tiktok_upload_avatar.ps1 -Tik 1 -ForceAvatarMachineList "11"`), runner kết thúc với lỗi:
`[AVATAR_WORKFLOW_FAILED] ENSURE_AVATAR: Avatar workflow failed: PROFILE_ROOT_NOT_CONFIRMED: Profile root was not confirmed`

## Phân tích chuỗi nguyên nhân (Root Cause Breakdown)
1. **Mục đích của Avatar-Only (`--avatar-smoke`):**
   - Chỉ mở Profile, tap nút sửa hồ sơ / bút chì (`TopLeftPencilLayout`), upload đè ảnh mới 512x512, verify kết quả trên Profile và thoát (`RELEASE`).
   - Hoàn toàn KHÔNG đăng video, không cần xác minh số lượng video tăng lên sau đăng (`post_verified`).

2. **Hành vi thừa thãi gây chết luồng trong `ACCOUNT_READY`:**
   - Tại `scripts/tiktok_workflow/state_machine.py` trong hàm `_handle_account_ready`:
     Code cũ chạy vô điều kiện:
     `current_baseline = self._count_profile_video_tiles_across_grid(profile_xml)`
   - Hàm này gọi `adapter.scroll_profile_grid(..., max_swipes=6, restore_top=True)`.
   - Tiến trình thực hiện 6 lần vuốt cuộn xuống lưới video, sau đó cố gắng vuốt ngược lại để trở về đỉnh trang Profile (`_restore_profile_grid_top`).

3. **Hiện tượng lỗi trên thiết bị thật (Galaxy S7 M11):**
   - Do độ nhạy màn hình và chuyển động ngón tay khi vuốt trong vùng lưới video, một video tile đã bị nhận diện là sự kiện tap.
   - Ứng dụng TikTok lập tức mở video toàn màn hình kèm thanh tương tác và modal bình luận (*"Đọc hoặc viết bình luận"*).
   - Thao tác `restore_top` không thể tìm thấy container lưới video nữa (`Không tìm thấy scroll container khi restore; dừng`).
   - Bước `ACCOUNT_READY` kết thúc và chuyển sang `ENSURE_AVATAR` trong khi màn hình thiết bị đang kẹt trong giao diện xem video!

4. **Vòng lặp Back thoát subpage bị kích hoạt sai:**
   - `ENSURE_AVATAR` phát hiện màn hình không phải Profile root nên gọi `_open_profile_root_recovered`, từ đó gọi `_leave_tiktok_subpages`.
   - Trong `_leave_tiktok_subpages`, bộ lọc `_is_tiktok_root_surface` kiểm tra các chuỗi loại trừ:
     `"thử mẫu này"`, `"thử mẫu trong capcut"`, `"sử dụng âm thanh"`.
   - Các video trên feed TikTok hiển thị sẵn huy hiệu CapCut hoặc âm thanh nền, khiến `_is_tiktok_root_surface` trả về `False` (hiểu nhầm trang xem video là một subpage cần back thoát ra).
   - Script thực hiện 12 lần `adapter.back()`, khiến TikTok bị đóng và văng ra màn hình chính điện thoại (`com.sec.android.app.launcher`).
   - Dù sau đó có cố gắng bring TikTok về foreground, việc tải lại giao diện gặp độ trễ lớn (SplashActivity) dẫn tới hết thời gian chờ và ném ngoại lệ `PROFILE_ROOT_NOT_CONFIRMED`.

## Giải pháp khắc phục O(1) chuẩn hóa
Trong `scripts/tiktok_workflow/state_machine.py`, chặn hoàn toàn việc đếm lưới video khi chạy ở các chế độ kiểm thử / smoke / avatar-only:

```python
is_smoke = bool(
    self.context.config.get("profile_smoke")
    or self.context.config.get("avatar_smoke")
)
if not is_smoke:
    current_baseline = self._count_profile_video_tiles_across_grid(profile_xml)
    baseline_scan = self._profile_grid_scan_reliability()
    if not self.context.post_baseline_locked:
        self.context.pre_post_video_count = current_baseline
        self.context.pre_post_profile_grid_scan = baseline_scan
    else:
        logger.info(
            "[ACCOUNT_READY] Giữ nguyên baseline trước Post đã khóa: %s "
            "(recapture hiện tại=%s)",
            self.context.pre_post_video_count,
            current_baseline,
        )
    logger.info(
        f"[ACCOUNT_READY] Profile video tile baseline: {self.context.pre_post_video_count} "
        f"(scan={baseline_scan})"
    )
```

## Bài học và nguyên tắc điều phối
- Không thực hiện bất kỳ thao tác vuốt cuộn nào trên màn hình nếu kết quả của thao tác đó không phục vụ trực tiếp cho mục tiêu của chế độ chạy hiện tại.
- Trong mọi chế độ smoke / avatar-only, màn hình Profile sau khi switch account thành công phải được giữ nguyên trạng thái tĩnh tuyệt đối cho đến khi bước `ENSURE_AVATAR` tiếp quản.
