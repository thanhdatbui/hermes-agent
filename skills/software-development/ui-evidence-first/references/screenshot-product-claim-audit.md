# Screenshot/Product-Claim Audit Reference

Use this reference when reviewing a social-media post, product screenshot, launch graphic, or marketing claim.

## Evidence matrix

| Claim class | Minimum evidence | Safe wording when incomplete |
|---|---|---|
| Feature exists | Canonical README plus implementation path or API route | “The repository documents/implements …” |
| Provider configured | UI label or config field | “A credential/config value appears present” |
| Provider reachable | Live provider check with status code | “Reachability was/was not verified” |
| Inference works | Real request, response, model ID, and logs | “End-to-end inference was/was not verified” |
| Tool use/streaming/reasoning | Dedicated request fixture or smoke test | “Advertised; compatibility remains unverified” |
| Free quota | Provider’s current terms/limits | “The project aggregates free tiers/credits; no guaranteed quota” |
| ToS compliance | Provider terms and exact usage pattern | “Publisher claims ToS compatibility; independent confirmation pending” |

## Recommended report order

1. **Project identity** — canonical URL, owner, current branch/version, and date checked.
2. **What the image visibly proves** — exact legible labels and values only.
3. **Source confirmation** — README/config/code paths matching the visible claims.
4. **Runtime gap** — what the screenshot does not prove and what test would prove it.
5. **Security review** — bind address, port, auth defaults, secret/OAuth persistence, outbound destinations, logging/redaction, installer behavior.
6. **Verdict** — real project / marketing overstatement / unverified claim / do-not-deploy recommendation.

## Common interpretation traps

- `Configured` is not `reachable`.
- `Running` is not `inference succeeded`.
- `Refresh models` is an action, not its result.
- A local endpoint shown as `localhost` does not prove the local model is loaded or tool-capable.
- A provider count in a post may be stale; compare the current catalog with the post date.
- “Use Claude Code free” can mean using Claude Code as the client while routing to non-Claude models.
- Aggregate token totals are not a personal allocation.
- “ToS-friendly” is not a vendor endorsement.
- A local-only Admin UI does not automatically mean the API proxy is private; inspect host binding and proxy authentication separately.

## Reusable concise Vietnamese wording

- “Ảnh xác nhận UI có mục X; chưa xác nhận request thật thành công.”
- “`Configured` chỉ cho biết config/key tồn tại, không chứng minh provider reachable.”
- “Con số token là tổng free-tier/credit theo claim của dự án, không phải quota được đảm bảo.”
- “Dùng Claude Code ở đây có thể chỉ là dùng client/agent; backend có thể là model provider khác.”
- “Tác giả tuyên bố ToS-friendly; chưa xem đó là chứng nhận của Anthropic/OpenAI.”
