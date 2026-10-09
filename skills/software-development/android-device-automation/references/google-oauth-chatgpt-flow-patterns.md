# Google OAuth & ChatGPT Web Registration Flow on Android (Chrome)

## Overview
Patterns and pitfalls when automating Google OAuth login/registration on Android Chrome (e.g., ChatGPT web registration via `hook_chatgpt_register.py`).

## Flow Stages & Detection

### 1. Direct Intent Launch
```bash
adb -s <device_id> shell am force-stop com.android.chrome
adb -s <device_id> shell am start -a android.intent.action.VIEW -d "https://chatgpt.com/auth/login" com.android.chrome
```

### 2. Cookie Consent & Entry Point
- Cookie dialogs often appear: Look for "Chấp nhận tất cả" / "Accept all".
- Entry button: "Tiếp tục với Google" / "Continue with Google".

### 3. Account Selection vs. Google Sign-In Branching
The OAuth flow branches into two distinct UX paths depending on device state:

1. **Account Chooser:**
   - Appears when Google accounts are already saved on device.
   - Node containing target email text exists directly on screen.
   - Action: Tap target email node coordinate.

2. **Google Sign-In Identifier (`accounts.google.com/v3/signin/identifier`):**
   - Appears when no matching session is saved.
   - Prompts "Đăng nhập bằng Google - OpenAI" / "Tiếp tục tới OpenAI".
   - **Pitfall - Email Re-typing:** If the loop checks `signin/identifier` repeatedly, it may re-type the email if the text field is already populated. Check if target email already appears in the XML or clear the field (`keyevent 67` loop) before typing.
   - **Pitfall - Next Button Obscuration:** Soft keyboard may obscure the "Tiếp theo" button (`[675,1722][1008,1776]`).
     - Always call `hide_keyboard(device_id)` or tap neutral top header (`input tap 540 200`) before clicking "Tiếp theo".
     - Locate "Tiếp theo" / "Next" button explicitly via UI hierarchy rather than blind coordinates.

### 4. Password Challenge (`accounts.google.com/v3/signin/challenge/pwd`)
- Detect keyword: `challenge/pwd`, `Enter your password`, or `Hiện mật khẩu`.
- Focus password field, clear any existing text, type password.
- Hide keyboard, click "Tiếp theo" or dispatch `keyevent 66` (Enter).

### 5. Onboarding / About You Form
- If first time logging into ChatGPT, page routes to `/about-you` asking for name and age / date of birth.
- Age input field (e.g. `540, 1218`), clear and enter calculated age (>= 18).
- Tap "Tiếp tục" / "Continue" and verify leaving the `/about-you` URL.

### 6. Verification Gate
- Wait until page settles on `chatgpt.com` main interface (look for "Message ChatGPT", "Hỏi bất cứ điều gì", or chat input bar).
- Take proof screenshot with timestamp.
