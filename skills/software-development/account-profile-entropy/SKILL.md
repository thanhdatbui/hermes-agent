---
name: account-profile-entropy
description: "Generate realistic Vietnamese account profiles (names, usernames, passwords) with high entropy to evade bot detection on platforms like Gmail, TikTok, Hotmail. Covers DEM_POOL for middle names, natural username patterns with dots/suffixes, and randomized password structures without fixed fingerprints."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [account-generation, bot-evasion, vietnamese-names, gmail-reg, tiktok-reg, entropy]
    related_skills: [tiktok-registration-ops, hotmail-outlook-automation, android-device-automation]
---

# Account Profile Entropy Optimization

Generate realistic Vietnamese account profiles that don't look like bot output. Used across Gmail reg, TikTok reg, Hotmail reg, and similar automation.

## When to Use

- Creating new account registration scripts that need to bypass platform bot detection
- Upgrading existing reg scripts that show pattern fingerprinting (fixed suffixes, no dots, rigid structures)
- Any automation where profile realism affects success rate

## Core Patterns

### 1. Name Structure (via `generate_random_name()`)

```python
DEM_POOL = [
    "Van", "Thi", "Ngoc", "Hoang", "Minh", "Quang", "Thanh", "Duc", "Dinh", "Huu",
    "Xuan", "Hai", "Thu", "Bao", "Anh", "Cong", "Trong", "Gia", "Tuan", "Phuoc",
    "Kim", "Tien", "Hong", "Phuong", "Khanh", "Duy", "Nhat", "Thao", "My", "Quoc",
]

# Distribution: 2-word (25%), 3-word (60%), 4-word (15%)
# Examples: "Tran Dung", "Bui Minh Tuyen", "Gia Duc Thanh Tuong"
```

### 2. Username Patterns (`build_username()`)

12+ natural styles, mixed randomly:

- **With dots**: `nguyen.an99`, `an.nguyen03`, `nguyen.van.an98`
- **Full name + year**: `nguyenvanan2001`, `annguyen04`
- **Date-based**: `nguyenan1508`, `an.nguyen.1508`
- **Location suffixes**: `nguyenan.vn02`, `annguyen.hcm99`
- **Random digits**: `nguyenan354`, `tranductoan04`

**Constraints**: 6-30 chars, no leading/trailing dots, no `..`, lowercase.

### 3. Password Patterns (`build_password()`)

9+ natural structures, random symbols (`@ # ! $`):

- `HoTenDDMMYYYY@` → `NguyenVanAn15082001@`
- `HoTen@YYYY` → `NguyenVanAn@2001`
- `TenHo#DDMMYYYY` → `VanAn#Nguyen15082001`
- `HoTen#WordYY` → `NguyenVanAn#Vn01`
- `WordHoTen#YY` → `VnNguyenVanAn#01`

**No fixed suffix** — never use `@Ks` or similar fingerprints across all accounts.
**Symbol compatibility**: Use `@`, `#`, `!`, `$` which are safely typed across `human_type` and `input_text` without interfering with space `%s` encoding.

### 4. Username Collision & Taken Retry Loop (`handle_username_entry()`)

When registering accounts, platforms frequently report that generated usernames are already taken ("đã được sử dụng", "That username is taken", "Try another", "Hãy thử tên khác").

- **Auto-retry budget**: Loop up to `max_username_attempts = 5` times before failing.
- **Synchronize in-place**: On collision, call `build_username(acc)` to generate a new candidate and immediately update `acc["id"] = new_username` and local `username = new_username`. This ensures downstream verification, success persistence (`persist_success_result`), and workbook logging record the actual registered username.
- **Clear field**: Call `type_edittext_node(..., clear=True)` (or `clear_field()` using `MOVE_END` + 60 `DEL` keyevents) before typing the new candidate.
- **Fail closed**: Only raise `RuntimeError(f"Username bị taken sau {max_username_attempts} lần thử: {username}")` after all retry attempts are exhausted.

### 5. Name Locale & Bot-Detection Tradeoffs (VN vs Foreign Names)

When automating account creation on phone farms (Samsung S7 / Android):

- **100% Vietnamese Names for Pure Gmail Reg**: Devices configured with Vietnamese locale (`vi_VN`, Samsung Vietnamese IME) running on Vietnamese ISP / proxy IPs should use **100% Vietnamese names** (2–4 words with `DEM_POOL`). This avoids any system/network/profile mismatch that triggers Google bot detection or `PHONE_VERIFY`.
- **Risk of Foreign Names on VN Locale**: Using English/foreign names (e.g. *John Smith*, *David Clark*) on a `vi_VN` device with a VN proxy triggers platform anomaly detection, sharply increasing Google `PHONE_VERIFY` triggers.
- **High Entropy without Name Collisions**: With `DEM_POOL` (30 middle names) combined with `HO_POOL` and `TEN_POOL` across 2-to-4-word distributions, Vietnamese names provide over 100,000+ natural combinations, ensuring near-zero collision probability without needing foreign words.

## Integration Point

```python
def generate_account_for_slot(slot, existing_emails=None, max_attempts=300):
    ho, dem, ten_chinh, ten = generate_random_name()
    acc = {
        "ho": ho,
        "dem": dem,
        "ten_chinh": ten_chinh,
        "ten": ten,
        "ngay": ngay, "thang": thang, "nam": nam,
    }
    acc["id"] = build_username(acc)
    acc["pass"] = build_password(acc)
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails | Fix |
|--------------|--------------|-----|
| Fixed 2-word names | Low entropy, collisions | Add DEM_POOL + 3/4-word distribution |
| Unescaped spaces in ADB typing | `adb shell input text` splits args on spaces → drops trailing words / leaves `firstName` empty → `STILL_ON_NAME` error | Encode spaces as `%s` in `input_text` or use KEYCODE_SPACE (`keyevent 62`) in `human_type` |
| Unescaped shell symbols in passwords | `#` is treated as shell comment, `&` as background, `(` `)` as syntax error | Use `keyevent 77` for `@`, `keyevent 18` for `#`, escape shell characters |
| Salt in middle of DOB (`nameabc1502`) | Obvious bot pattern | Use dots, natural combos, suffixes |
| Fixed password suffix (`@Ks`) | Cross-account fingerprint | Random symbols + random structures |
| No dots in username | Unrealistic for VN users | Include `.` in 50%+ patterns |
| Immediate abort on taken username | Wastes machine preflight, proxy rotation, and UI progress when 1 candidate collides | Implement `handle_username_entry()` retry loop up to 5 times with `build_username()` + sync `acc["id"]` + `clear=True` |

## Verification

- Generate 1000+ samples, verify uniqueness rate > 99.9%
- Visual inspection: outputs should look like real VN users
- No duplicate patterns across batches

## References

- `references/gmail-reg-case.md` — Case study from `register gmail` repo