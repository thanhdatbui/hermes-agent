# OmniRoute Sol vs ChatGPT Web Surface

## Trigger
Use this reference whenever a user asks to consult “GPT Web Sol”, “Sol high”, “Sol Auditor”, `review`, or `plan/review` during closeout or code review.

## Correct routing
In the Taadaa closeout design, these names normally refer to an HTTP model route through OmniRoute, not a browser interaction:

- Endpoint: `http://localhost:20129/v1/chat/completions` (or the resolver's healthy local/LAN candidate)
- Default closeout model alias: `review`
- Accepted related aliases include `plan-review`, `plan-review-hard`, and `chatgpt-web/gpt-5.6-sol-high` when explicitly selected/configured.
- Health evidence: `GET /api/health` returning HTTP 200.
- Review evidence: closeout output containing the model route, scorecard, `Verdict`, and exit code.

## Pitfall
Do not interpret “GPT Web Sol” as “open chatgpt.com in a browser” unless the user explicitly asks for the browser/UI surface. Browser/CDP failure is irrelevant if the OmniRoute endpoint is healthy and the closeout gate already returned a model verdict.

## Closeout diagnosis lesson
A prior failure came from opening ChatGPT Web/CDP and then reporting Sol as blocked, even though `closeout_gate.py` had already routed the review through OmniRoute and returned `APPROVED`. The correct first action is to inspect `closeout_gate.py` routing and its live health/review evidence, not to launch a browser.

## User question framing
When asked why closeout did not run fully, separate:
1. **Trigger interpretation:** progress questions such as “xong hết chưa?” are status requests, not closeout commands; explicit “chốt phiên/chốt/đóng phiên/kết thúc phiên/done/wrap up” triggers closeout.
2. **Coordinator execution error:** once an explicit closeout command is received, do not stop at “logic done/test pass”; run the mandatory gate immediately.
3. **Provider routing:** report whether OmniRoute review actually ran based on endpoint/model/verdict evidence; never claim it was not called merely because no browser tab was opened.
