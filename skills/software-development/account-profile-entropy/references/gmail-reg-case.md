# Case Study: Gmail Reg Name Entropy Optimization

## Context
Repo: `D:\Taadaa\register gmail\gmail_reg_v10.py`
Issue: Bot detection patterns in username/password generation

## Before (Anti-Pattern)
```python
# Only 2-word names
ho = random.choice(HO_POOL)
ten = random.choice(TEN_POOL)

# Username: rigid salt pattern
salt = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(2, 3)))
choice_mode = random.randint(1, 3)
if choice_mode == 1:
    return f"{ho}{ten}{salt}{ngay}{nam[-2:]}"  # nguyenanabc1502
# ...

# Password: fixed fingerprint
return f"{Ho}{Ten}{ddmmyyyy}@Ks"  # 100% accounts share @Ks suffix
```

## After (Optimized)
```python
DEM_POOL = [30 middle names]

def generate_random_name():
    # 2-word (25%), 3-word (60%), 4-word (15%)
    ...

def build_username(acc):
    # 12+ patterns with dots, suffixes, random digits
    choices = [
        f"{ho_s}.{ten_chinh_s}{nam2}",
        f"{ho_s}{ten_chinh_s}{ngay}{thang}",
        f"{ho_s}{ten_chinh_s}{random.choice(suffixes)}{nam2}",
        # ... 9 more patterns
    ]
    u = random.choice(choices).strip(".").replace("..", ".")
    # enforce 6-30 chars
    return u

def build_password(acc):
    # 9+ structures, random symbols, no fixed suffix
    choices = [
        f"{ho_t}{full_ten_t}{dob_full}{sym}",
        f"{ho_t}{full_ten_t}@{nam}",
        f"{ten_t}{ho_t}#{dob_full}",
        # ... 6 more patterns
    ]
    p = random.choice(choices)
    # ensure uppercase, lowercase, digit, symbol present
    return p
```

## Sample Outputs
```
[01] Name: Hau Thao Nhung | DOB: 14/06/2001 | Email: nhunghau354@gmail.com | Pass: ThaoNhung#Hau2001
[02] Name: Mau Huu Chi | DOB: 08/02/2002 | Email: mau.huu.chi02@gmail.com | Pass: MauHuuChi@Plus02
[03] Name: Bui Minh Tuyen | DOB: 25/06/2002 | Email: tuyenbui209@gmail.com | Pass: TuyenBui#25062002
[04] Name: Gia Duc Thanh Tuong | DOB: 03/11/1998 | Email: tuongducthanhgia23@gmail.com | Pass: VnGiaTuong1998%
```

## Review Result
- 9Router Qwen3.6-Max-Preview: **VERDICT: APPROVED**
- Minor findings (non-blocking):
  1. Duplicate pattern in username choices (easy dedupe)
  2. Password truncation before validation (move after)
  3. Redundant fallback in DEM_POOL filter
  4. Hardcoded 'A' prefix for missing uppercase (randomize position)

## Files Changed
- `gmail_reg_v10.py` (+217/-14 lines)
- `docs/farm-automation-cases.md` (+Case GMAIL-REG-NAME-ENTROPY-01)
- `docs/uiautomator.md` (+Case GMAIL-REG-NAME-ENTROPY-01)

## Related
- `android-device-automation` — ADB shell text typing and space encoding rules
- `tiktok-registration-ops` — TikTok reg uses similar profile generation
- `hotmail-outlook-automation` — Hotmail change-info may reuse patterns

## ADB Typing Compatibility (GMAIL-REG-NAME-INPUT-SPACE-01)
When integrating multi-word names (having spaces in `ten`) and symbols into ADB workflows:
- `input_text(device_id, text)`: Must encode spaces as `%s` (e.g. `part.replace(' ', '%s')`). Otherwise `/system/bin/input text` splits args on space and aborts, leaving fields empty.
- `human_type(device_id, text)`: Must type spaces with `keyevent 62` (KEYCODE_SPACE), `@` with `keyevent 77` (KEYCODE_AT), `#` with `keyevent 18` (KEYCODE_POUND).

## Username Collision Handling (GMAIL-REG-USERNAME-TAKEN-RETRY-01)
When Google indicates username taken ("đã được sử dụng", "That username is taken", "Try another", "Hãy thử tên khác"):
- `handle_username_entry(device_id, acc, user_node, max_username_attempts=5, stt=0, shot_fn=None)`
- Retries up to 5 times generating fresh candidates via `build_username(acc)`.
- Updates `acc["id"] = new_username` and local `username` so all downstream verify and success logging record the final registered username.
- Clears field (`clear=True`) before typing the next candidate.