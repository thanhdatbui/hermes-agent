# Email Validation, Target Eligibility, and Night Chain Pipeline Patterns

## 1. Email Screen Detection vs Validation Error (`social_reg_v1.py`)

### Pitfall: Header Match False-Positive
In `detect_after_continue(device_id)`:
- The title/header of the email entry screen contains text like `"Nhập địa chỉ email"` or `"Enter email address"`.
- If `form_hints` checks for substring `"nhap dia chi email"` or `"hop le"` (from `"Nhập địa chỉ email hợp lệ"`), it matches the standard static screen header immediately, before user input is even submitted or validated.
- This misclassifies normal screen state as `form_still_visible` (email validation error / not submitted), causing premature aborts or invalid loop behavior.

### Safe Implementation Pattern
- Narrow the error detection to unambiguous validation error strings:
  ```python
  validation_error_hints = [
      "khong hop le",             # "không hợp lệ" — error "Nhập địa chỉ email hợp lệ"
      "invalid email",
      "valid email",
  ]
  if any(h in flat for h in validation_error_hints):
      edittexts = list_edittext_nodes(xml)
      if edittexts and not any(n.get("password") for n in edittexts):
          log("   → detected: form still visible (email validation error / not submitted)")
          return "form_still_visible"
  ```
- In `fill_email_and_next()`:
  - Track `had_form_error = False` alongside `had_network_error = False`.
  - On `result == "form_still_visible"`:
    ```python
    log(f"   ✗ {em}: Phat hien validation error ro rang tren form email")
    save_ui_xml(device_id, f"fail_{stt}_form_error_{idx}")
    had_form_error = True
    shell(device_id, "input", "keyevent", "4")
    time.sleep(1.5)
    continue
    ```
  - Priority at loop exit:
    ```python
    if had_form_error:
        raise RuntimeError(f"[07] Khong the dang ky email cho STT {stt} do loi form validation ('{em}')")
    if had_network_error:
        raise RuntimeError(f"[07] Khong the kiem tra email cho STT {stt} do loi mang ('Khong co ket noi Internet')")
    raise RuntimeError(f"[07] Tat ca {len(candidates)} email cua STT {stt} da co TK TikTok")
    ```

---

## 2. Target Eligibility Machine Account Counting (`tiktok_target_eligibility.py`)

### Invariant: Decouple STT Machine Counts from TikTok ID
When parsing target rows in `load_registered_mailboxes(*, return_machine_counts=True)`:
- `registered.add(mailbox_key(email))` requires both `email` and `tiktok_id` to be considered registered.
- However, machine slot distribution (`machine_counts[m]`) must count every assigned machine row with a valid non-empty STT, regardless of whether `tiktok_id` is populated yet.
- Gating `machine_counts[m] += 1` inside `if tiktok_id and stt_idx is not None:` leads to severe undercounting of active accounts per machine slot when scanning partially populated sheets.

### Correct Pattern:
```python
if email and tiktok_id:
    registered.add(mailbox_key(email))
if stt_idx is not None and stt_idx < len(row):
    raw_stt = row[stt_idx]
    if raw_stt is not None and str(raw_stt).strip():
        try:
            m = int(raw_stt)
            machine_counts[m] = machine_counts.get(m, 0) + 1
        except (TypeError, ValueError):
            pass
```

---

## 3. Night Chain Pipeline Farm Error Budget vs Script Failure (`run_night_chain_pipeline.py`)

### Alert Gate Invariant
In `scripts/run_night_chain_pipeline.py`:
- Each phase (Phase 1 Gmail, Phase 2a TikTok Reg, Phase 2b Feed, Phase 3 2FA) may exit non-zero due to individual machine/device operational failures on the farm (e.g. timeout, captcha, device offline).
- If the batch successfully executed and reported results for targets (`total > 0`), the operational results are handled by `batch_aggregator` and fleet error budget. **Do not send high-priority Telegram failure alerts for routine farm device failures.**
- Pipeline alerts should only fire if the phase runner crashed, failed to start, or produced 0 total targets.

### Phase 2a Pattern:
```python
tiktok_reg_code, tiktok_reg_out = run_tiktok_reg_batch()
if tiktok_reg_code != 0:
    tiktok_reg_details = parse_tiktok_details(tiktok_reg_out)
    if not (isinstance(tiktok_reg_details, dict) and int(tiktok_reg_details.get("total", 0) or 0) > 0):
        if "Total targets: 0" not in tiktok_reg_out and not ("Targets: 0" in tiktok_reg_out and "TOTAL=0" in tiktok_reg_out):
            _send_night_chain_alert(
                "Phase 2a (Reg TikTok)",
                tiktok_reg_code,
                parse_summary_line(tiktok_reg_out, "TikTok"),
                str(TIKTOK_REG_REPO_DIR / "social_reg_log.txt")
            )
```
