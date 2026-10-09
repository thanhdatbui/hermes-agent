# Live Codex OAuth + 5SIM verification preflight

## Why this exists
Live verification is side-effectful: it can start a GPM browser, create an OAuth session, spend 5SIM balance, and create an OmniRoute connection. Validate every identity and gate before spending.

## Reproduction lessons

### 1. Full GPM UUID validation
A requested profile UUID can differ from the actual GPM UUID by one character. In the observed case, the command used a UUID containing `...1df1...`, while the local GPM API contained the matching email under `...1df2...`. The wrong UUID returned `PROFILE_NOT_FOUND`.

Before starting:

- Query `GET http://127.0.0.1:19995/api/v3/profiles/<full-uuid>`.
- If not found, query the paginated profiles list and match by normalized email/name.
- Do not start the profile or buy a number until the UUID/email mapping is confirmed.

### 2. Interpreter and import smoke test
The script under test removed every `sys.path` entry containing `hermes-agent`. When the default interpreter's `site-packages` lived under that path, the script failed before doing any work with `ModuleNotFoundError: requests`.

Durable fix pattern:

- Run the smoke test with the exact interpreter intended for the live run:
  `python -c "import requests, playwright; print('imports ok')"`
- Compile before live execution:
  `python -m py_compile D:/Taadaa/GPM auto/scripts/codex_5sim_auto_verify.py`
- If path sanitization is necessary, preserve valid `site-packages`; otherwise use a known-good Python installation. This is an execution-environment fix, not evidence that the OAuth flow itself is broken.

### 3. 5SIM and OmniRoute gates
Observed preflight checks showed that the 5SIM API can expose prices/stock for both VN and Colombia, while `total_active_orders` can be zero even when historical orders exist. Use the authenticated activation-orders endpoint with the correct category when reconciling current orders.

For the live flow:

- Check balance and active orders before and after.
- Check VN `virtual34` availability before purchase.
- Purchase only after the page is confirmed to be OpenAI's real phone-verification form.
- On rejection, timeout, missing OTP, or missing OmniRoute connection ID, cancel immediately and verify the order is no longer active.
- Finish the order only after `poll-callback` returns a connection ID.
- Confirm the GPM stop endpoint was called and record its result.

### 4. Evidence contract
The final report must include:

- Process exit code and complete outcome status.
- Reason and screenshot path for any manual block.
- All 5SIM order IDs, states, cancellation/refund results, final balance, and active-order count.
- GPM stop confirmation.
- OmniRoute poll response and connection ID, or the precise reason it was absent.

Never summarize a preflight or planned rerun as a completed live verification.
