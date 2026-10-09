# Antigravity 403 Forbidden ("Verify your account to continue") & GCP ToS Re-authentication

## Overview & Pathology
When an Antigravity OAuth connection in OmniRoute / proxy fails with:
```json
{
  "error": {
    "message": "[403]: Antigravity upstream error (403)",
    "type": "permission_error",
    "code": "insufficient_quota"
  },
  "upstream_details": {
    "error": {
      "code": 403,
      "message": "Verify your account to continue.",
      "status": "PERMISSION_DENIED"
    }
  }
}
```
This error is NOT a quota exhaustion or an expired token. It indicates that Google Cloud Platform requires the account to accept/re-accept Google Cloud Terms of Service (ToS) or complete interactive account verification before downstream Antigravity inference is permitted.

## Diagnostic & Remediation Flow via CDP (Port e.g. 61117 / Custom Profile)

1. **Inspect Live Browser Context via CDP:**
   - Connect Playwright or a CDP script to the running Chrome CDP endpoint (e.g. `http://127.0.0.1:61117`).
   - Identify existing pages:
     - Google Cloud Console: `https://console.cloud.google.com/welcome/new?...`
     - OAuth Account Chooser: `https://accounts.google.com/v3/signin/accountchooser?...redirect_uri=http%3A%2F%2F127.0.0.1%3A20129%2Fcallback...`

2. **Step 1: Accept GCP Terms of Service:**
   - On the GCP Console page (`console.cloud.google.com`), locate the ToS checkbox:
     - Selector: `input[type='checkbox']` (specifically the one labeled *"I agree to the Google Cloud Platform Terms of Service..."*).
     - Check the checkbox (`await cb.check(force=True)`).
   - Click the submission button:
     - Button labeled `Agree and continue` (or `button:has-text("Agree and continue")`).
   - Pitfall: `await page.screenshot()` on Google Cloud Console can timeout waiting for dynamic web fonts (`Page.screenshot: Timeout 30000ms exceeded. waiting for fonts to load...`). Do not block automation on font-loaded screenshots; verify state via DOM query (`input[type='checkbox']` count drops to 0, or modal disappears).

3. **Step 2: Complete OAuth Consent:**
   - Navigate to / focus the OAuth tab (`accounts.google.com`).
   - Click the corresponding Google account email (e.g. `benghowelltpkf1@gmail.com`).
   - If prompted for permissions / consent ("Google Antigravity wants to access..."), click `Allow` / `Continue`.
   - Ensure the callback URL (`http://127.0.0.1:20129/callback?...`) receives the code and returns HTTP 200 / success.

4. **Step 3: Verification via Real Inference:**
   - Trigger the connection test endpoint:
     `curl -s -X POST http://127.0.0.1:20129/api/providers/<connection-id>/test`
   - Test with actual inference via proxy:
     ```bash
     curl -s -X POST http://127.0.0.1:20129/v1/chat/completions \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer omniroute-default-key" \
       -H "x-omniroute-connection: <connection-id>" \
       -d '{"model":"antigravity/claude-sonnet-4-6","messages":[{"role":"user","content":"ping"}]}'
     ```
   - Verify that 403 Forbidden is cleared and streaming/response returns valid completion tokens.
