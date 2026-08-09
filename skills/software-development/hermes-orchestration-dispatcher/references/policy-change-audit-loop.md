# Policy-Change Audit Loop — AGENTS.md scope-split v4→v7 (2026-08-06)

Kế hoạch sửa AGENTS.md để cho phép "Hermes flash worker patch consumer-normal" đã chạy
7 vòng plan→audit. Chi tiết v1–v3 nằm trong SKILL.md; file này ghi v4→v7 + quyết định cuối.

## Tóm tắt hành trình

| Vòng | Plan | Auditor | Verdict | Lý do cốt lõi |
|---|---|---|---|---|
| v1 | v4-pro (29KB) | Sol | REJECT (6) | lossless chưa chứng minh, root >3KB, marker test fail, split 6 file không auto-load |
| v2 | sau 3 quyết định user (fallback ngang hàng) | Sol | REJECT (8) | live gate cấm+cho fallback, `unavailable` chưa fail-closed, thiếu canonical-path gate |
| v3 | 1 canonical fallback contract | Sol | REJECT (6) | trộn model/transport, effective pin không chứng minh, dispatch generation né cap |
| v4 | bỏ fallback khỏi policy text | Sol | REJECT (7) | **Direct Fallback section cũ vẫn mâu thuẫn**; tool auto-route phá live gate; Model Routing vẫn chép |
| v5 | + worker-identity verify | Sol | REJECT (7) | identity verify sau side effect; "no fallback in policy" lại nhắc Hermes/9router; vẫn duplicate |
| v6 | session-as-worker (fallback duy nhất) | Sol | REJECT (7) | vẫn nhắc Transport fallback/external CLI; section "Both Worker Routes Fail" cũ nằm NGOÀI vùng sửa; spawn unknown chưa fail-closed |
| v7 | 3 vùng sửa + marker manifest + plan gate | Sol 429→401; **ds-v4-pro** | **APPROVE_WITH_FIXES** (5 FIX spec-gap) | 8/8 findings v6 đã fix; 6/7 PASS; 5 FIX nhỏ (rename heading, định nghĩa reconciliation/command class, ai decide handoff, làm rõ 2 plan gate) |

## Quyết định user cuối (đã chốt — ghi vào rule `D:\Taadaa\HERMES_SUBAGENT_RULES.md`)

1. **Luna/high ≡ v4-flash/max là worker NGANG NHAU** — pin lệch model KHÔNG phải lỗi, không
   có downgrade khi session deepseek làm live. Đây là chính sách user, không tranh cãi với auditor.
2. **BỎ HẲN fallback model khỏi policy** — fallback khi hết quota/outage là cơ chế TOOL layer
   (Hermes `fallback_providers`, 9router auto-route), cài trong tool setting, KHÔNG ghi vào rule dự án.
3. **Session-as-worker = fallback DUY NHẤT**: spawn worker subagent CONFIRMED fail
   (runtime-unavailable / capability-unavailable / dispatch-429 có source+provider+pin) →
   ghi `SUBAGENT_RUNTIME_UNAVAILABLE` trước side effect → session tự làm worker bằng model
   session (Hermes=ds, Codex=luna). KHÔNG model substitution, KHÔNG identity verification
   (session model biết chắc). Timeout/unknown/ambiguous → KHÔNG session-as-worker; reconcile
   (prove không còn worker/session/process/lease/action) → không chứng minh được →
   `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` → `FINAL_BLOCKED`.
4. Worker theo scope (pinned): consumer-normal → ds-v4-flash/max; live/recovery/lock/core → luna/high.
5. Plan gate: session-as-worker làm LIVE phải có execution plan trước (actions, lock/lease,
   stop gates, verifier, rollback) — áp dụng MỌI session-as-worker live, không chỉ task mới/khó.

## 5 FIX v7 (ĐÃ ÁP vào file thật 2026-08-06 → APPROVE)

1. Rename heading → `### Session-as-Worker Reference` (bỏ ám chỉ "2 routes"). ✅
2. Định nghĩa "reconciliation" = prove 5 resources absent (subagent PID, session handle, process tree,
   lease file, action log) bằng system queries; absence-of-evidence ≠ evidence-of-absence. ✅
3. Ai decide handoff → "coordinator, dùng pre-recorded verifier proof + (khi cần) Terra/Sol advice". ✅
4. Định nghĩa "command class" = {code-edit, config-change, package-build, deployment, recovery,
   lock-op, verification}. ✅
5. Làm rõ 2 plan gate: mandatory execution plan do coordinator soạn; Sol/high advisory plan THÊM
   cho task mới/khó/architecture-sensitive. ✅

Sau khi áp 5 FIX → file audit thật (ds-pro) APPROVE_WITH_FIXES (1 WARN heading → fix → APPROVE) →
ad-hoc verify 24/24 PASS → final hash `59ae6155b27fac7b37fe5228dda12314e6d2723eaf9bda8c2dc9b40f64bbcac9`.

### Pitfall verify script: grep cấm phải giới hạn trong vùng sửa

Script verify chạy grep toàn-file `9router`/`fallback_providers` → **false positive FAIL**: các pattern
này HỢP LỆ ở section khác (DeepSeek Quota Fallback L1020+, audit wrapper `invoke-*-9router-audit.ps1`
L1037-1554). Finding Sol chỉ cấm nhắc 9router TRONG vùng sửa. → Verify script phải lấy offset các
sentinel rồi grep CHỈ trong 3 vùng đã sửa; marker `SUBAGENT_RUNTIME_UNAVAILABLE` giảm 1 là CHỦ Ý
(xoá đoạn external-CLI-fallback cũ) — check "decrease ≤1 (intentional)", không check post>=pre cứng.

## Bài học class-level

- **Policy-change plan của model yếu (v4-pro) gần như luôn bị model mạnh (Sol) REJECT nhiều vòng**.
  Đừng tự động chạy vòng N+1 mãi: sau ~3 vòng cùng 1 gốc, hãy chỉ ra cho user rằng chính quyết
  định policy của họ (VD fallback ngang hàng) là gốc rễ, và đề xuất đơn giản hoá (session-as-worker,
  bỏ fallback khỏi policy) — đó là hướng thoát thực tế.
- **"Fallback model" là khái niệm dễ bị lạm dụng nhất trong policy**: auditor sẽ bắt (a) định nghĩa
  unavailable lỏng (transport/timeout/output kém ≠ model chết), (b) ping-pong né attempt cap,
  (c) effective pin không chứng minh được. Đưa fallback xuống tool layer + session-as-worker
  (model biết chắc) là cách hết vòng lặp.
- **Policy 97KB chồng chéo**: sửa 2 section → đụng section kế (Coordinator Direct Fallback L187+)
  → phải mở rộng vùng sửa → đụng tiếp. Trước khi sửa policy lớn: inventory TOÀN FILE các câu
  "sole worker"/fallback/profile-mismatch, xác định mọi vùng bị ảnh hưởng, KHÔNG anchor bằng line
  number (heading sentinel + assert unique/order trước edit).
- **AGENTS.md Taadaa không thuộc git, đang được user chỉnh tay** (hash đổi 2 lần trong session).
  Trước khi sửa tự động: snapshot SHA-256 ngay trước edit + verify hash bản copy; nếu file đang
  biến động tay → báo user, đừng đè.

## 9router model availability (kiểm chứng 2026-08-06)

- `cmc/deepseek/deepseek-v4-flash` + `v4-pro`: OK (pro có `reasoning_content`; cần `tool_choice=none`
  chống fake tool_calls).
- `gpt-5.6-luna/terra/sol` (bare + `cx/` prefix): OK khi GPT upstream sống. **Khi upstream chết:
  429 usage-limit → sau reset lại 401 token_invalidated** — không phải lỗi cấu hình 9router, là
  token Google/OpenAI upstream hết hạn; phải user sửa trên dashboard.
- `v98/claude-opus-4-8`/`claude-sonnet-4-6`: 403 payload lớn (key bị giới hạn input) → chỉ OK
  request nhỏ; không dùng cho audit plan lớn.
- `cmc/moonshotai/Kimi-K2.6`: OK nhưng `finish=length` hay cắt giữa chừng → chia vòng hỏi tiếp.
- Fallback chain audit khi Sol/terra chết: **ds-v4-pro vẫn cho verdict hợp lệ** (APPROVE_WITH_FIXES v7).
