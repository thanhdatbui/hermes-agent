# GPM & CDP Automation: NVIDIA NIM Registration Runbook

## Key Findings & Automation Gotchas

### 1. NVIDIA Sign-In Modal (`build.nvidia.com/explore/discover?modal=signin`)
- **Breakpoint Visibility Bug**: The `Next` submit button has CSS classes `hidden md:min-w-[100px] lg:inline-block`. When running in certain GPM window viewports, Playwright's `locator("button:has-text('Next')").click()` will throw `TimeoutError: element is not visible`.
- **Reliable Solution**: Use keyboard event `email_input.press("Enter")` directly in the input field to trigger the email resolution.

### 2. Form Flow & Routing
- New email automatically routes to `https://login.nvgs.nvidia.com/v1/create-account`.
- Password fields (Password + Confirm Password) and Terms of Use checkboxes are populated before clicking `Create Account`.
- Verification email is sent to the Hotmail/Outlook inbox to complete account activation and retrieve the `nvapi-...` key.
