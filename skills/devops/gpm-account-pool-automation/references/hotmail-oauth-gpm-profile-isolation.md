# Hotmail OAuth → GPM profile isolation

## Canonical mapping

For ChatGPT onboarding through Hotmail Direct Email + OTP:

- One Hotmail account gets one dedicated GPM profile.
- The profile uses the fixed proxy belonging to the S7 machine that contains that Hotmail.
- Profile names must retain machine/proxy/email lineage, e.g. `M06_<hotmail>_P5106` or `<proxy_port>_<hotmail>`.
- Do not add Hotmail to an existing Gmail-S7 profile when the goal is clean ChatGPT lineage; mixed cookies make ownership and later cleanup ambiguous.

## Preflight manifest

Before side effects, build and review a manifest containing:

`machine → S7 serial → raw proxy/port → Hotmail → token/client_id → GPM profile name/id`

Read the Hotmail row from `gmail_clean_v2.xlsx` and resolve its proxy by machine from `PROXYgandienthoai.xlsx`; never infer a port from an email or choose arbitrary first rows. OAuth flows require both refresh token and client ID.

## Execution boundary

A request to “login 5 GPM profiles” means only:

1. create/find the dedicated GPM profile;
2. assign the mapped proxy before browser start;
3. login Hotmail and preserve its session;
4. capture profile/session/artifact evidence.

Do not silently proceed to ChatGPT registration, OmniRoute sync, or Google SSO. Run accounts sequentially and verify one account before starting the next.

## Ambiguity gate

If the user has not identified which five accounts to use and several OAuth candidates exist, list the exact candidates and stop before creating profiles or logging in. Do not select “the first five” and then ask for confirmation after side effects.

## Evidence

For each account retain: profile name/id, machine, serial, proxy port, success/failure status, and artifact screenshot/log path. A success claim without these readbacks is unproven.
