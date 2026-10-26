# Case Study: Phantom ChatGPT Registration, Exit Code Traps, and OpenAI Onboarding Discrimination

## 1. Context & Incident Summary
In October 2026, an audit of the Taadaa Farm GPM Hotmail lifecycle supervisor (`batch_gpm_5profiles_supervisor_state.json`) reported that 564 accounts on the Admin cluster (M201–M280) and 81 accounts on the Kibe cluster were in stage `DONE` or `WAIT_7D` with `chatgpt_registered_at` timestamps recorded.
However, when an autonomous feeder attempted to extract ChatGPT-Web session cookies for OmniRoute, opening these profiles revealed that:
1. Over 500 profiles had never completed ChatGPT registration.
2. Opening ChatGPT on these profiles redirected to `/about-you` ("Bạn bao nhiêu tuổi?" / "How old are you?") or `/create-account/password`.
3. Only 85 accounts across the entire farm had ever successfully completed registration with working session cookies.

---

## 2. Root Cause Analysis (Three-Stage Cascading Failure)

### Bug 1: CLI Returncode Trap in `chatgpt_gpm_direct_reg.py`
The CLI runner `main()` had two structural exit code flaws:
```python
# FLAW A: Exiting 0 when no candidate matched the requested filter
candidates = get_gpm_candidates(limit=args.limit, email_filter=args.email, ...)
if not candidates:
    logger.info("Không có ứng viên nào cần đăng ký ChatGPT.")
    return 0  # <--- FALSE POSITIVE: Caller assumes registration succeeded!

# FLAW B: Unconditional exit code 0 regardless of registration status
for c in candidates:
    res = register_chatgpt_gpm(c, ...)
    logger.info(f"Kết quả {c['email']}: {res['status']}")
return 0  # <--- FALSE POSITIVE: Exits 0 even on FAIL_PASSWORD_NOT_FOUND, FAIL_WRONG_OTP, or ERROR!
```

### Bug 2: Cross-Cluster Workbook Partition Blindspot
In `get_gpm_candidates`:
```python
if provider == "hotmail":
    cred = get_hotmail_credentials(em)
    pwd = get_pass_chatgpt_from_updated_workbook(em)
    if not pwd:
        logger.warning(f"[{em}] Thiếu PASS CHATGPT; bỏ qua Hotmail candidate.")
        continue
```
`get_pass_chatgpt_from_updated_workbook` only parsed `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`. The Admin cluster workbook (`admin/taikhoan_dat_v2_updated .xlsx`) only contained 10 columns (lacking column 11 `PASS CHATGPT`).
Consequently, 100% of Admin Hotmail accounts evaluated `pwd = None`, logged a warning, and resulted in `candidates = []`.

### Bug 3: Supervisor Blind State Advancement
`batch_gpm_5profiles_supervisor.py` executed `chatgpt_gpm_direct_reg.py` via `run_cmd()`. Because of Bug 1, the subprocess exited with code `0`. The supervisor interpreted `proc.returncode == 0` as complete registration success:
```python
ok_chatgpt = run_cmd([...])
if ok_chatgpt:
    info["chatgpt_registered_at"] = now()
    # Advanced to WAIT_7D -> CHANGE_INFO -> DONE phantomly!
```
Accounts progressed through a 7-day soak and password change cycle despite never having registered on OpenAI.

---

## 3. UI Discrimination: New Registration vs Expired Session

When automating OpenAI/ChatGPT authentication, operators must distinguish between two fundamentally different UI states:

| Screen / URL | Meaning | Action Required |
| :--- | :--- | :--- |
| **`auth.openai.com/about-you`**<br>("Bạn bao nhiêu tuổi?" / "How old are you?") | **Account is UNREGISTERED** or onboarding was interrupted. OpenAI requires Full Name and Age to complete initial account creation. | Must fill Name + Age (e.g. 25), click Continue/Tiếp tục, and wait for redirect to `chatgpt.com` before session cookies exist. |
| **`auth.openai.com/create-account/password`** | **Email has never been registered** on OpenAI. | Account was never created. Must enter new password and proceed through onboarding. |
| **`auth.openai.com/email-verification`**<br>("Kiểm tra hộp thư đến của bạn") | **Account ALREADY EXISTS**, but browser session cookie expired. | OpenAI is requesting a temporary 6-digit OTP code sent to Hotmail. Fetch OTP via Microsoft Graph API and enter code. |
| **`chatgpt.com` with `#prompt-textarea`** | **Active Authenticated Session**. | Extract `__Secure-next-auth.session-token` immediately. |

**Crucial Operator Rule:** Seeing "Bạn bao nhiêu tuổi?" (`/about-you`) proves that the account was never previously registered. It is not an existing session challenge.

---

## 4. Microsoft Graph API OTP Retrieval Quirks

1. **Pre-Validation of Refresh Tokens:**
   - Hotmail refresh tokens in `gmail_clean_v2.xlsx` expire over time.
   - Always validate tokens via `https://login.microsoftonline.com/common/oauth2/v2.0/token` before launching browser profiles. An expired grant returns `AADSTS70000: invalid_grant`. Skipping invalid tokens upfront prevents launching hundreds of dead browser instances.
2. **Subject & Sender Filter Traps:**
   - OpenAI OTP emails do NOT always contain the word `"openai"` in the subject line!
   - English: `"Your temporary ChatGPT verification code"`
   - Vietnamese: `"Mã xác minh tạm thời của bạn cho ChatGPT"`
   - Sender: `noreply@tm.openai.com`
   - **Correct Regex:** Match both `"openai"` and `"chatgpt"` across combined subject and sender:
     ```python
     is_openai_msg = bool(re.search(r"openai|chatgpt", f"{subject} {sender}", re.IGNORECASE))
     ```
3. **Password Fallback for Hotmail:**
   - If `PASS CHATGPT` column is missing in cluster workbooks, fall back to `normalize_password(cred.get("pwd") or "Taadaa123@")` rather than aborting candidate selection.

---

## 5. Verification Checklist
- [ ] `chatgpt_gpm_direct_reg.py` returns `1` when `--email` does not find a candidate.
- [ ] `chatgpt_gpm_direct_reg.py` returns `1` when registration fails (`res["status"]` is not `SUCCESS`, `ALREADY_LOGGED_IN`, or `DRY_RUN_OK`).
- [ ] Cross-cluster Excel lookup reads both `kibe/gmail_clean_v2.xlsx` and `admin/gmail_clean_v2.xlsx`.
- [ ] Supervisor state (`chatgpt_registered_at`) is only set when actual token/cookie is confirmed or CLI exit code is verified non-zero on failure.
