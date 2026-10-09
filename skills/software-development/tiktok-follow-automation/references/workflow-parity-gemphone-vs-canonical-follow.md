# Workflow parity: GemPhone vs canonical follow runner

Use this reference when a user compares a canonical TikTok follow consumer with a GemPhone/GemLogin flow.

## Evidence-first comparison
Read both workflow sources and compare exact semantics, not appearances:

- target source and target quality;
- action order, feed/search entry, dwell and delay;
- post-action verification and reload timing;
- retry/recovery behavior;
- state persistence, failure classification, and cooldown;
- whether labels such as `Nhả flow` mean a real follow-drop check or only loop termination.

Do not infer causality from avatar provenance or a generic statement that both workflows "lướt dạo". If both use video-frame avatars and automated browsing/following, those are not discriminating variables.

## Three states that must not be conflated

Keep these separate in logs and analysis:

1. `FOLLOWED`: the fresh post-action UI proves the relationship state.
2. `SYNC_DELAY/UI_UNPROVEN`: the expected state is not visible yet, or the reload/selector path is not proven; this is not a platform drop.
3. `FOLLOW_DROP`: an independent, fresh re-check proves the relationship was not retained.

**Kỷ luật khi User xác nhận đối soát:**
Khi người vận hành đã đối soát dữ liệu thực tế với TikTok Dashboard / Tracker DB và xác nhận số lượt follow bị trừ/mất: TUYỆT ĐỐI CẤM tiếp tục bao biện "do sync delay". Đây là hiện tượng **TikTok Silent-Drop thật** từ phía nền tảng.

## Cân nhắc các biến số khi so sánh Farm vs Kênh Mẫu (User Corrections)

1. **Proxy cùng gói mạng/nhà cung cấp:**
   Khi farm và kênh mẫu dùng chung gói mạng/proxy, CẤM đổ lỗi cho "proxy bẩn". Biến số proxy được loại trừ.

2. **Cơ chế Fallback Mode 2 -> Mode 1:**
   Khi Mode 2 (follow followers) cạn anchor hoặc gặp lỗi, runner đã có cơ chế tự động fallback sang Mode 1 (search UID). Không quy chụp Mode 2 là nguyên nhân làm hỏng toàn bộ phiên follow.

3. **Inbound Trust vs Outbound-only Action:**
   Khác biệt mấu chốt giữa kênh mẫu (giữ được follow) và nick farm (bị nhả follow) nằm ở **Tài sản nội dung & Inbound Trust**:
   - Kênh mẫu đã có video cắn đề xuất (hàng chục ngàn view, 88K likes), có lượng người xem thật tương tác đổ vào (inbound). Nền tảng nâng ngưỡng trust cho tài khoản, cho phép outbound follow được giữ lại.
   - Nick farm mới chỉ có chiều tương tác đi (outbound) mà chưa có lượng tương tác thật đổ vào (inbound = 0). Hành vi outbound follow của nick chưa có trust dễ bị kích hoạt bộ lọc chống spam/bot của TikTok và bị silent-drop.

A crude workflow may appear healthier because it never checks state and therefore never records failure. A strict verifier may also harm throughput if it reloads too soon, repeats navigation, and converts `SYNC_DELAY/UI_UNPROVEN` into `FOLLOW_FAILED` and cooldown. This is a hypothesis until fresh run artifacts or a bounded A/B comparison confirms it.

## GemPhone interpretation
A typical search-follow GemPhone flow may be only:

```text
warm-up scroll -> search UID from text/file -> open exact profile -> tap Follow -> next UID/end loop
```

A label such as `Nhả flow` can mean loop exit, not follow-drop verification. Do not attribute reload verification, Mode 2 follower-list behavior, age/video gates, or cooldown to the original GemPhone flow unless the source actually contains them.

## Canonical-runner interpretation
The canonical consumer may intentionally include stronger engineering controls: semantic identity binding, Mode 1/Mode 2, post-tap verification, state/budget accounting, and progressive cooldown. These are engineering safeguards, not proof that the platform will reward the flow. A robust implementation can still have a platform-outcome bottleneck if post-action verification is too eager or if the account has weak inbound content signals.

## Outcome vs engineering quality
Report two axes separately:

- **Engineering robustness:** correctness of selectors, identity binding, evidence, state, and fail-closed recovery.
- **Observed platform outcome:** retained follows, inbound views/likes/followers, recommendation history, and actual live artifacts.

An account with recommendation-driven inbound history is not comparable to a new/low-signal account solely because both ran a follow script. Conversely, a successful-looking GemPhone run without retention checks is incomplete evidence, not proof that its workflow is superior.

## Discriminating test
Do not rewrite the runner based on this hypothesis alone. Use a bounded offline/mock or explicitly approved live A/B design:

- hold account eligibility, target quality, budget, proxy/device cohort, and content exposure constant;
- compare immediate verification/reload against delayed independent retention verification;
- record the three states above, reload count, time-to-state, and confirmed retention;
- keep Mode 1/search targets separate from Mode 2/follower-list targets before attributing causality.

When presenting the result, state what source code proves, what fresh artifacts prove, and what remains unproven. If the user corrects an earlier causal story, retract that unsupported claim directly and return to source-grounded comparison; do not replace one confident guess with another.
