# VIDEO_PICK metric fail trên video render-random (Tik2) — 2026-08-13, máy 45

Bằng chứng đầy đủ cho root cause: `VIDEO_PICK_TARGET_UNVERIFIED` similarity 0.09-0.18
dù toàn bộ pipeline data ĐÚNG. Đây là metric fail, không phải data/ADB/máy.

## Hiện tượng

Batch Tik2 `batch_tik2_list_49_20260813_092614` (49 máy, MaxParallel 16 sau tuning):
- 19x `VIDEO_PICK_TARGET_UNVERIFIED`, 17x `POST_SUBMISSION_UNKNOWN`, 48 lỗi / 49 target.
- Mẫu máy 45 (`ce0716071586c80602`): video `D:\TIKTOK-videonuoinick\354\3.mp4`,
  log `best similarity=0.179 < threshold=0.350` lặp 3 lần → MANUAL_REVIEW.

## Bằng chứng data ĐÚNG (loại trừ từng giả thuyết)

1. **Push OK**: log `Pushing ... (11.7MB) -> /sdcard/DCIM/Camera/codex_45_3_run_..._092716.mp4`
   → `Push thành công`. `ls` trên device: file 12,252,504 bytes tồn tại.
2. **MediaStore index OK**:
   `adb shell content query --uri content://media/external/video/media --projection _id,_display_name,datetaken`
   → `Row: 0 _id=1539, _display_name=codex_45_3_run_ce0716071586c80602_20260813_092716.mp4`
   → file vừa push CÓ trong MediaStore. Không stale.
3. **Tile picker hiện ĐÚNG video**: `video-pick-grid.png` chỉ có 1 tile — người đội mũ
   chấm bi, áo kem, ngoài trời, emoji 😌❤️, badge `00:13`. Frame extract từ
   `354\3.mp4` (ffmpeg `-ss 0.15`, 13.0s, 12.2MB): CÙNG nhân vật/cảnh/sticker.
   Vision xác nhận "rất tương đồng/chính là nhân vật đó".

## Đo correlation thật (PIL thuần, không numpy — venv thiếu numpy)

- Tile crop từ `video-pick-grid.png` bounds (3,350,360,707) [tile 357x357 thật, bắt đầu
  sau tab bar] vs mọi frame {0.0,0.15,0.35,0.6,0.85,1.5,3.0}: **0.092-0.159**.
- Full-frame vs full-screen artifact `video-pick-target-verify.png`: 0.130 — SAI vì
  artifact là full screen 1080x1920, KHÔNG phải tile crop (pitfall!).
- Self correlation = 1.0 → thuật toán đúng, ảnh thật khác nhau ở mức pixel.

## Root cause

Thumbnail TikTok trong picker = **crop 1:1 vuông + badge thời lượng + vòng tròn chọn +
nén mạnh (compression artifacts)**. Video Tik2 render-script-random có emoji/sticker
nội dung + chuyển động → pixel correlation 64x64 grayscale vỡ dù nội dung đúng 100%.
Video Tik1 (render tay "ông A") thumbnail sạch → correlation cao → pass.
Đối chứng: máy 38 cùng batch Tik2 pass video pick (0.608) — video đơn giản hơn.

## Hướng fix (chưa implement)

Đổi metric trong `_verify_video_tile_identity` (state_machine.py ~10113) từ
pixel-correlation 64x64 sang feature match: ORB/SIFT + ratio test hoặc color
histogram (HSV) — nhạy crop/overlay/nén nhưng vẫn xác nhận đúng cảnh. Đo thử
ORB trên tile-vs-frame TRƯỚC khi chốt ngưỡng.

## Quy trình verify ngoài luồng chuẩn (khi nghi metric fail)

1. `ffmpeg -y -ss 0.15 -i <video> -frames:v 1 frame.png` (chú ý venv thiếu numpy;
   dùng PIL thuần: getdata + mean-subtract correlation).
2. Crop tile THẬT từ `video-pick-grid.png` — KHÔNG dùng `video-pick-target-verify.png`
   (full screen). Tìm bounds bằng scan hàng: tab bar trắng std≈0 (y≈168-340),
   tile bắt đầu nơi std>0 (y≈350-700), tile 1:1 ~357px.
3. vision_analyze tile crop + frame: giống mắt thường + corr thấp = metric fail.
4. Xác nhận push + MediaStore trước (2 lệnh ADB ở trên) để loại data.

## POST_SUBMISSION_UNKNOWN timing (m38 cùng batch)

`POST 09:37:37 → VERIFY_POST 09:37:37 → submission state UNKNOWN (no ACCEPTED evidence)`
— VERIFY_POST chạy ~2s sau tap Post, TikTok chưa kịp xác nhận. Fail-closed đúng,
nhưng đây là timing issue: cần chờ/recapture profile đủ thời gian TikTok xử lý
trước khi kết luận post fail. Check khoảng cách POST→VERIFY trong execution.log
trước khi chẩn đoán.
