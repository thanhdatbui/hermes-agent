# Read-Only ChatGPT-Web / Codex Inventory

Use this procedure when the request is a narrow inventory of GPM profiles linked to OmniRoute providers.

## Allowed sources
- GPM Local API: `GET http://127.0.0.1:19995/api/v3/profiles` (paginate using the returned pagination fields; do not assume the first page is complete).
- OmniRoute: `GET http://127.0.0.1:20129/api/providers`, reading `connections[]`.
- Only explicitly targeted logs/workbooks already named by the task. Do not scan profile directories, open GPM profiles, launch browsers, inspect cookies, or mutate provider/profile state.

## Reconciliation
1. Extract email from the GPM profile `name`; normalize to lowercase.
2. Extract email from both OmniRoute `name` and `email`; normalize to lowercase.
3. Match `chatgpt-web` connections to GPM profiles by normalized email.
4. Treat Codex as **active** only when the matching `provider == "codex"` connection has `isActive == true`. An inactive Codex row is still useful evidence that a Codex connection exists, but it does not satisfy “no active Codex provider”.
5. Preserve ChatGPT provider state separately: report both `isActive` and `testStatus`; `testStatus == "banned"` is not equivalent to a healthy active provider.

## Age evidence gate
- A provider `createdAt`, GPM `created_at`, workbook update date, `CHATGPT_READY`, `ALREADY_LOGGED_IN`, or a generic successful-login log is **not by itself proof** that ChatGPT registration occurred at that time.
- Registration age is eligible only when a targeted source explicitly records a dated ChatGPT registration/completion event, or supplies an independently dated session/registration artifact whose meaning is unambiguous.
- If the evidence cannot prove `>=48h`, write `UNKNOWN`; never infer age from account age, profile age, provider creation time, or a successful session.
- Failed direct-registration attempts, OAuth failures, guest sessions, and “already logged in” outcomes are not registration-age proof.

## Output contract
Return a concise table with: email, GPM ID/name, ChatGPT provider status, Codex status, registration evidence/age, and eligibility. Include excluded rows when they explain why a seemingly matching account is not eligible. State the number of eligible candidates explicitly. If none pass the age gate, say `0 eligible`, not “probably eligible.”
