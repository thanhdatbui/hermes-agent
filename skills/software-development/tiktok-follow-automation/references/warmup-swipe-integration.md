# Warm-up swipe integration (feed → follow)

Quyết định kiến trúc 2026-08-15 (user): warm-up lướt feed trước follow KHÔNG viết
mới trong `tiktok-follow` — nối module feed-swipe có sẵn của
`D:\Taadaa\tiktok-luot nuoi acc` (python_runner) đứng TRƯỚC bước follow.

## Tư vấn đã chốt với user
- Warm-up TRƯỚC UID đầu tiên đáng giá nhất: pattern bot dễ bị rate-limit nhất là
  mở app → search → follow ngay, không xem gì. 1–2 phút lướt feed đầu session làm
  session nhìn tự nhiên.
- Xen giữa các follow KHÔNG cần nhiều: canary thật follow 7 UID liên tiếp OK
  (máy 1 & máy 2, 2026-08-15) không cần swipe giữa; runner đã có 1 swipe sau mỗi
  follow (`verify_after_tap._confirm_not_released` — confirm follow không bị nhả).
- FOLLOW_FAILED là cơ chế bảo vệ đúng — KHÔNG lách bằng cách swipe thêm khi TikTok
  bắt đầu không nhận follow (dừng session theo quy tắc).

## Câu hỏi mở cần trả lời trước khi implement
- Có cần GIẢM số lượt swipe bên feed khi nối vào không? Bên feed hiện swipe random
  số lượt. Warm-up chỉ cần count NHỎ bounded (3–5), KHÔNG phải cả nurture session.

## Facts khảo sát (2026-08-15)
- `python_runner/flows/feed_swipe_smoke.py` — file chính, RẤT LỚN (~17,930 dòng),
  đọc bằng `read_file` phân đoạn / `grep -n` chứ không đọc nguyên.
- Randomization (grep "random" trong file):
  - `random.randint(requested_min_total_videos, requested_max_total_videos)` —
    tổng video mục tiêu cho session (xung quanh dòng 14633).
  - `videos_until_tab_decision = random.randint(3, 8)` (dòng 16021/16031) — số video
    trước khi quyết định chuyển tab.
  - `random.uniform` cho thời gian watch/post-swipe + `random.randint` jitter tọa độ
    swipe (dòng 11056–11104), like/follow rate ngẫu nhiên theo % (dòng 11192, 11299).
- Caps/constants:
  - `SESSION_MAX_SWIPES_CAP = 15`, `MAX_SWIPES_CAP = 3`,
    `SESSION_TOTAL_VIDEOS_CAP = 30`.
  - `_max_swipes(ctx)` đọc `ctx.config["_max_swipes"]` (default 1) — config-driven.
- CLI entry: `python_runner/run_tiktok.py` với `--mode feed-session-smoke` /
  `--mode multi-machine-feed-session`, cờ `--max-swipes N` (1–15),
  `--like-rate`/`--follow-rate` JSON percent, `--allow-feed-swipe`,
  `--allow-navigation-only`, `--allow-benign-popup-dismiss`, `--allow-like`,
  `--prepare-tiktok` (chỉ multi-machine), `--recovery-test-swipes N` (1–3).
- Module layout: `python_runner/{core,flows,scheduler,scripts,tools,tests}`;
  swipe flow chính `flows/feed_swipe_smoke.py`; popup/classifier
  `flows/benign_popup.py` + `core/classifier.py`; account switcher `core/account_
  switcher.py`.

## Governance (BẮT BUỘC đọc trước khi sửa)
- `D:\Taadaa\tiktok-luot nuoi acc\AGENTS.md` rất nghiêm:
  - Coordinator → direct worker policy: mọi write/build/live phải qua đúng 1 fresh
    worker (deepseek-v4-flash / gpt-5.6-luna, role=worker), không nested delegation.
  - Recovery contract: mọi live target theo DETECTED → … → VERIFIED_SUCCESS |
    FINAL_BLOCKED, lock giữ tới verified final, không blind-retry cùng signature.
  - DEFERRED_LOCKED: lock active/foreign/busy giữ nguyên, không force-unlock.
  - Audit ladder: bounded tasks không audit ngoài mặc định; auto-recovery mới cần
    AG_CLAUDE_AUDIT → OPENCODE_AUDIT → CODEX_FALLBACK_AUDIT (dừng ở verdict đầu).
  - Shared UI compatibility: đổi selector/popup/coordinate phải cập nhật
    `automation-core/docs/ui-compatibility-contract.md` + `docs/ui-compatibility.md`
    + regression tests.
- `tiktok-follow/AGENTS.md` — quy trình canary riêng (xem SKILL.md chính).

## Khuyến nghị khi implement
1. TDD cả 2 phía: feed (swipe bounded) + follow (gọi feed trước follow) — test cả 2
   repo, vì thay đổi nối chéo consumer.
2. Warm-up bounded: cấu hình `_max_swipes` hoặc `--max-swipes 3–5` cho pha warm-up,
   KHÔNG dùng session mặc định 15.
3. Cân nhắc đặt trong `tiktok-follow` như một pre-step gọi module feed (giữ follow
   repo là canonical entry), hoặc 1 script orchestrate mới trong tiktok-follow gọi
   `run_tiktok.py --mode feed-session-smoke` trước `run_follow.py`.
4. Verify warm-up: swipe count thực tế + feed confirmed (XML for-you) trước khi bước
   sang search/follow; nếu warm-up fail → fail-closed, không follow tiếp.
5. Canary: 1 máy, budget 1, lock-clean như quy trình live canary hiện tại.
