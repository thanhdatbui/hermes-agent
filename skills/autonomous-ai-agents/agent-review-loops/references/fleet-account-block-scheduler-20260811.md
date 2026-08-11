# Fleet Account-Block Scheduler — pipeline 8 phase end-to-end (2026-08-10/-11)

Ví dụ hoàn chỉnh nhất của large-job pipeline (plan → audit plan → build phase → audit phase).
Repo: `D:\Taadaa\tiktok-luot nuoi acc`, plan `.hermes/plans/2026-08-10_fleet-account-block-scheduler.md` (1151 dòng sau 3 vòng sửa).

## Timeline & runtime thật (ước lượng vòng sau)

| Bước | Model/đường | Số lượng | Runtime thật |
|---|---|---|---|
| Planner viết plan (866 dòng) | luna subagent | 1 lần | ~29 phút |
| Audit plan vòng 1 | luna subagent | 1 | ~17.5 phút → MINOR_FIXES (3 MAJOR fact: baseline sai, math formula, constants lệch) |
| Planner sửa plan vòng 2 | luna | 1 | ~37 phút |
| Audit plan vòng 2 | luna | 1 | ~19 phút → MINOR_FIXES (2 residual) |
| Planner sửa vòng 3 | luna | 1 | ~17 phút |
| Audit plan vòng 3 | luna | 1 | ~34 phút → **APPROVED** |
| Build phase (worker) | luna subagent | 8 phase | 8–45 phút/phase (Phase 3 45' hết tool limit, cần worker nối tiếp 26') |
| Audit phase (luna) | luna subagent | 5 lần | 5–27 phút/lần |
| Audit phase (AG Claude sonnet-4-6 qua 9router) | run-ag-audit.sh | 7 lần | **10–41 giây/lần** (nhanh hơn luna ~30-50x) |

Bài học: AG Claude qua 9router audit phase rẻ + nhanh (10-41s) — dùng cho mọi audit phase khi diff chứa trọn production change; luna subagent khi commit test-only pin hoặc cần đọc toàn bộ code ngoài diff.

## Chuỗi commit cuối (master)

`050d2e1`+`d039f53` (P1 window+residual) → `f1744bf` (P2 blocks.py) → `ea2c76a`→`dd8db90` (P3 picker+manifest, 4 fix audit) → `c45e98a`→`848fc7f` (P4 validation, 3 fix audit) → `0748787` (P5 test-pin) → `33f6c4d` (P6 maintenance) → `6a49d51` (P7 adversarial). 173 passed từ baseline 121. 15 commit tổng.

## Vòng audit Phase 3 (mẫu loop đóng gate đầy đủ)

1. Audit: REJECT — block metadata splice (đổi account + rehash → vẫn ACCEPTED); entry_ids sorted() bỏ lọt đảo thứ tự.
2. Fix `fc61be9`: bind metadata + exact order → Audit: REJECT — seed bypass source-less + test gate-masked.
3. Fix `edcb71f`: seed unconditional + tách test → Audit: MINOR — 3 mutation (machine/account/account_row) reject ở feed-check (411) không phải source-mapping (434) = gate-mask.
4. Claude CLI fix `904ae86` (test reshape sync dependent fields) → Audit AG: MINOR — 1 hypothetical (account row modulo) + NIT comment.
5. Fix `dd8db90` (assert phòng thủ 1 dòng) → **AG APPROVED** (10.5s).

Pattern: production fix theo vòng audit chỉ khi finding có locator đối chiếu được; finding hypothetical đóng bằng evidence (probe in line reject 434 cho cả 3 mutation), không bằng code.

## Số liệu hit pattern đáng nhớ

- Worker báo "ad-hoc verification PASS" thay vì suite green: 7+ lần (mặc định luna) — xem SKILL.md mục ad-hoc.
- AG Claude findings hypothetical/false-positive: ~60% (Phase 4: 2/3 MAJOR thật, MINOR sau đó 3/3 hypothetical) — luôn đối chiếu code + probe trước khi fix.
- Boundary guard production đã đúng từ Phase 1 residual (`d039f53`) → Phase 5 chỉ cần test-pin — audit phải được báo trước "guard đã tồn tại từ commit X, không phải baseline trap" nếu không auditor REJECT oan "thiếu production change".
