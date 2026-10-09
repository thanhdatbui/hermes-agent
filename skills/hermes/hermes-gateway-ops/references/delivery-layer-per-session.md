# Delivery-layer audit: one session per Telegram message

Use this when auditing cron/script output, delivery fan-out, or a request to send each logical session as a separate Telegram message.

## Trace the complete producer→delivery→adapter path

1. Start at the producer. For cron `no_agent` jobs, inspect `cron/scheduler.py:run_job` and `_run_job_script_with_claim_heartbeat`: script stdout is captured, trimmed, and returned as one `str`. Do not assume newline-separated output already has message boundaries.
2. Follow `cron/scheduler.py:run_one_job`: the final response is converted into one `deliver_content`, then `_deliver_result(...)` is called once. Multiple delivery targets mean fan-out to different chats/platforms, not multiple messages in one chat.
3. Follow `_deliver_result(...)`: wrapping/header/footer, media extraction, origin/topic resolution, and live-adapter/standalone fallback all operate on one content string. Check both branches before concluding behavior from only the live gateway path.
4. Follow `gateway/delivery.py:DeliveryRouter._deliver_to_platform`: it receives one `content` string and calls `adapter.send(...)` once per target. `splits_long_messages=True` is a long-payload capability, not a logical-session delimiter.
5. Inspect the Telegram plugin (`plugins/platforms/telegram/adapter.py`) and standalone sender (`tools/send_message_tool.py`) separately. Telegram chunking is driven by the 4096 UTF-16 limit after formatting; it does not split on blank lines, session markers, or stdout records. The standalone sender also chunks after formatting and may handle media/captions independently.

## Contract distinction to preserve

- **Logical message split:** the producer supplies `list[str]` (or a formally framed record stream), and the delivery layer loops over records, preserving each record as one logical send.
- **Transport chunk split:** one logical content string is divided only because a platform length limit requires it. These chunks are not separate sessions and may carry continuation indicators.
- **Target fan-out:** one logical content is sent to multiple destinations. This must not be confused with either kind of split.

## Safe design for per-session delivery

Prefer an explicit structured contract such as `delivery_messages: list[str]` alongside the full audit document. Persist the complete unmodified output for local audit, but deliver each non-empty list item separately. Avoid guessing boundaries with `\n\n` unless the producer guarantees that delimiter cannot occur inside a session. If text framing is unavoidable, use a documented JSONL/record protocol with escaping and malformed-record behavior.

When changing this behavior, audit all of these invariants:

- one delivery call per logical session, in source order;
- one failed send is observable and cannot silently mark the whole batch successful;
- headers/footers are applied per message only when intended;
- topic/thread metadata is preserved for every message;
- media tags are extracted per message, not across session boundaries;
- full output remains saved even if one Telegram send fails;
- Telegram's 4096 UTF-16 chunking remains a transport fallback inside each logical message;
- live-adapter and standalone delivery paths implement the same record contract.

## Common audit conclusion

If the code path has `content: str` → one `_deliver_result(...)` → one `adapter.send(...)`, it currently has no per-session delivery protocol. Report the exact producer, loop, and adapter call sites; do not claim that Telegram's long-message chunker solves logical session separation. No code change is implied by an audit unless the user explicitly asks for implementation.
