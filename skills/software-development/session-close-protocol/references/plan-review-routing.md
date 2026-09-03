# Plan-review routing and evidence

Use this reference for code-review gates in session closeout, especially lock/recovery and state-machine work.

## Required route

1. Select the class-level review model from the task:
   - ordinary repository work: `plan-review`;
   - lock, recovery, persistence, concurrency, or state-machine work: `plan-review-hard`.
2. Call that named model through the configured review transport, normally 9Router at `http://127.0.0.1:20128/v1/chat/completions`.
3. Bind the request to the exact staged candidate: record staged paths, `git write-tree`, per-file hashes or an equivalent exact byte manifest, and include only those bytes in the review input.
4. Require a parseable first-line verdict such as `VERDICT: APPROVED`, `VERDICT: MINOR_FIXES`, or `VERDICT: REJECT`.

## Do not silently downgrade

The session model and implementation workers are not auditors. In particular, do not substitute Luna/Flash or a worker delegation for `plan-review`/`plan-review-hard` merely because it is available. A review response is valid only when all three are true:

- the request named the required plan-review model;
- the response contains a parseable verdict;
- the transport did not fail or silently map the request to an unsupported implementation model.

Check the raw route/model evidence when possible. A 200 response alone is not approval. An API error saying the effective model is unsupported is a route failure, not a verdict. If a named route (for example `plan-review-hard`) is advertised by `/v1/models` but the completion response reports a different effective implementation model or a Codex-account incompatibility, classify it as `BLOCKED_AT_REVIEW`/route failure; do not relabel that response as plan-review and do not use Luna as a substitute.

## Fallback

If the primary AG route lacks credentials or the named plan-review route is unavailable, record the exact non-secret route error and use the configured independent audit fallback. Keep the fallback read-only and explicitly label the actual model/route in the report. If no independent route returns a parseable verdict, stop at `BLOCKED_AT_REVIEW`; do not commit or push.

## Freshness

Any edit, worker handoff, index rebuild, rebase, or staged-byte change invalidates prior review and test evidence. Re-read and re-hash the scoped files, rebuild the exact index candidate, rerun focused verification, and request a fresh review. A worker `APPROVED`/`REJECT` is diagnostic only and cannot authorize Git release actions.

## Minimal request contract

Use a non-streaming, read-only request:

```json
{
  "model": "plan-review-hard",
  "reasoning_effort": "high",
  "stream": false,
  "tools": [],
  "tool_choice": "none"
}
```

Never put credentials in the prompt or persist them in review artifacts. Review prompts should state the exact acceptance criteria, staged file hashes/tree, test scope, and the forced verdict format.

### 9Router Authentication Key Discovery

When dispatching plan-review over Python script to `http://localhost:20128/v1/chat/completions`:
```python
with open('C:/Users/Kibe/AppData/Local/hermes/auth.json') as f:
    data = json.load(f)
key = data.get('providers', {}).get('9router', {}).get('api_key', '') or data.get('providers', {}).get('custom:9router', {}).get('api_key', '')
```
Pass `Authorization: Bearer <key>` in headers.

### Review Payload Sizing & Socket Timeout Safety (Anti-Hang Invariants)

1. **Focused Diff-Scoped Payload (Context Optimization):**
   - Chặn đứng tình trạng model bị nghẽn do prompt quá nặng: Chỉ truyền `git diff -U3`/`-U5` cho các file thay đổi trong scope và nội dung các test case mới liên quan.
   - Tuyệt đối không nhét toàn bộ git diff của nhiều repository hoặc hàng nghìn dòng mock/fixture boilerplate vào prompt.

2. **Socket Timeout & Fail-Fast Protection:**
   - Khi gọi API review từ script Python (`urllib.request.urlopen(req, timeout=45)` hoặc `requests.post(..., timeout=45)`), **BẮT BUỘC đặt timeout ở socket layer** (khuyến nghị 45s–60s).
   - Tuyệt đối không để lệnh `terminal` foreground chờ vô hạn (300s+) khi proxy/upstream bị kẹt socket. Nếu socket timeout kích hoạt, lập tức fail-fast để thử lại hoặc chuyển route fallback.

3. **OmniRoute (:20129) Multi-Account Pool & Semaphore Diagnosis:**
   - OmniRoute chạy tại `:20129` với combo pool (ví dụ `ag-gemini-pool-3` gồm 13 account Antigravity) sử dụng chiến lược `priority` (Ordered Active/Standby with Concurrency Spillover, `maxConcurrent=5` mỗi account).
   - Khi gặp lỗi `SEMAPHORE_TIMEOUT` trên một connection cụ thể (ví dụ `antigravity:conn:218efa02`), điều này chứng minh request đã tràn qua các target trước đó và bị kẹt hàng đợi tại connection đó do toàn bộ pool đang chạm trần tải đồng thời, không phải do OmniRoute không chịu đổi account.
   - Khi cần review tải nặng, OmniRoute hỗ trợ `failoverBeforeRetry: true` giúp nhảy ngay sang account tiếp theo trong pool nếu gặp lỗi 429/503.

### Handling Reviewer REJECT Iterations

When reviewer returns `VERDICT: REJECTED`:
1. Read the exact findings carefully (check for anti-minefield invariants, blind actions, fail-closed gaps, or overbroad filters).
2. Fix every finding directly on the candidate source and test files.
3. Invalidate previous test runs, re-run focused and regression tests to prove GREEN.
4. Issue a fresh review request with the new candidate diff until `VERDICT: APPROVED` is achieved. Never stop closeout halfway on a REJECT.

## Evidence to retain

Record:

- selected route and effective model;
- route errors, with credentials redacted;
- staged path allowlist;
- staged tree/file hashes;
- exact parseable verdict and findings;
- verification command/result immediately before review.
