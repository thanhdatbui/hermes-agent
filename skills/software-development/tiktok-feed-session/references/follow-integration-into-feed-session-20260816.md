# Follow-integration vào Feed Session (chốt 2026-08-16)

Nguồn: plan `D:\Taadaa\tiktok-luot nuoi acc\.hermes\plans\2026-08-15_follow-integration-from-follow-repo.md`
+ quyết định user 2026-08-16. Contract đầy đủ:
`tiktok-follow-automation/references/feed-follow-chaining-contract-20260816.md`.

## Hook gọi follow cuối phiên (subprocess, không import)

- Vị trí: `multi_machine_feed_session.py`, sau `child_result = _result_from_child_context(...)`
  (~dòng 909), khi `child_result.final_status in {"success", "degraded"}`.
- Lệnh: `python "D:\Taadaa\tiktok-follow\follow_runner\run_follow.py" --machine N
  --config "D:\Taadaa\tiktok-follow\follow_runner\config.example.yaml" --account-row-index R`
- `N` = máy vừa lướt, `R` = account row index (switcher đã đổi nick xong; follow runner
  chỉ verify identity). UID target = random trong cột ID hợp lệ của `taikhoan_run_safe.xlsx`.
- Budget 5–10/phiên nằm trong config follow — repo này KHÔNG truyền.
- Gate sensitive: feed fail login/OTP/2FA/captcha/security → KHÔNG gọi follow; fail khác
  (kẹt UI/ATX/capture) → VẪN gọi (follow runner tự force-stop + relaunch).
- Đọc exit code (0=OK) + stdout `FOLLOW_RESULT <json>` → ghi vào kết quả phiên.

## Ghi follower mỗi phiên (user đổi 2026-08-16)

- KHÔNG đợi cuối ngày — ghi state JSON per-machine ngay sau mỗi phiên
  (`record_follower_in_state` bên follow repo). Export Excel gom riêng
  (`python -m follow_runner.export_follower_tracking`).

## Tỉ lệ feed hiện tại (code `feed_swipe_smoke.py`)

| Tab | Distribution | Watch | Like | Follow |
|---|---|---|---|---|
| Đề xuất (for-you) | 98% | 2-8s | 12% | 5% → **12%** (Task 1) |
| Bạn bè (following) | 2% | 1-5s | 7% | 0% |
| Friends | 0% | 1-3s | 2% | 0% |

- Tab "Bạn bè" (`Bạn bè`/`Friends`) TÁCH RIÊNG khỏi "Đã follow" (`Đã follow`/`Following`)
  trong TikTok UI — 2 tab, friends = follow 2 chiều, following = 1 chiều.
- Follow organic CHỈ ở for-you (người lạ); following/friends follow_rate=0 (bạn bè không
  follow được) — đúng thiết kế.
- Like 7% following là hợp lí (bạn bè ít like hơn người lạ 12%, không phải 0).
- Lướt Bạn bè (friends) TRÌ HOÃN ~15 ngày (đợi nick kết bạn 2 chiều sau follow chéo).

## Quy tắc an toàn — user BỎ 2026-08-16

- BỎ: không đối xứng cùng ngày / không vòng khép kín / rải giờ / không follow 2 nick cùng IP.
- User: "mẫu số random trong 480 acc cũng lớn nên cứ để nó chạy kệ mẹ".
- Chỉ GIỮ: FOLLOW_FAILED = dừng phiên (chạm trần) + budget 5–10/phiên + tỉ lệ organic:cross.

## Lịch: 2 phiên → 3 phiên/acc/ngày

- Hiện tại: 3 block × 2 phiên = 6 phiên/ngày/máy (3 acc) — cần 3 phiên/acc = 9 phiên/ngày/máy.
- Sửa picker sinh 3 phiên/acc (giữ pair-gap 60–90').
