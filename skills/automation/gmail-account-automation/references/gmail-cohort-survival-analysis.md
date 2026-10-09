# Gmail cohort survival analysis

## Purpose
Compare current Gmail LIVE/DIE outcomes for accounts that were used for a service (for example ChatGPT) against accounts that were not, without presenting an observational association as a trust-score experiment.

## Read-only procedure

1. **Inventory sources and snapshot times.** Prefer the canonical manager workbook plus append-only service-status/event data. Record exact paths, sheet names, `updated_at` values, and whether each status is current or historical.
2. **Normalize identity.** Lowercase and trim email addresses; deduplicate across workbook sheets. Count each Gmail once per analysis snapshot.
3. **Build exposure labels from positive evidence.** `service_used` requires an explicit success/attempt event such as `CHATGPT_READY`, an OmniRoute/service-success record, or a timestamped attempt log. Missing notes are not automatically proof of idle; keep `UNKNOWN` when telemetry is incomplete.
4. **Define outcome and window.** `LIVE`/`DIE` must be tied to a check timestamp. Do not mix OpenAI task failure with Gmail survival: Cloudflare, OTP, password, WebView, and timeout failures are `service_attempt_failed`, not Gmail `DIE`.
5. **Show raw counts.** For every cohort report `LIVE`, `DIE`, `UNKNOWN`, denominator, rate, snapshot date, and exclusions. Formula: `LIVE rate = LIVE / (LIVE + DIE)` only when unknowns are excluded explicitly.
6. **Stratify before interpreting.** Compare within similar Gmail age/creation cohort, source batch, 2FA state, machine/proxy exposure, and follow-up window. Mixed Excel serial dates, text dates, and missing dates must be normalized or labeled `UNKNOWN`.
7. **Audit selection bias.** If service processing only accepted accounts already LIVE, aged, 2FA-ready, or cooldown-passed, the service-used group is selected from survivors. A higher LIVE rate there cannot establish that service use improved trust.
8. **Use conservative language.** A single current snapshot supports association only; it cannot identify a causal effect. Do not claim that ChatGPT registration raises Gmail trust or that idling is always harmless.

## Recommended telemetry
Record append-only events with: `email`, `gmail_created_at`, `service_name`, `service_attempt_at`, `service_outcome`, `gpm_login_at`, `checkmail_at`, `gmail_status`, `failure_reason`, `2fa_state`, source batch, machine/proxy, and a fixed follow-up checkpoint (for example day 1/7/14/30). Preserve pre-exposure status so the cohorts can be aligned.

## Known interpretation pattern
A cohort showing 95% LIVE after ChatGPT/GPM use versus 62% LIVE among idle accounts is not evidence that ChatGPT protected Gmail when the used cohort was prefiltered for survival/2FA/cooldown. Investigate eligibility rules and checkpoint causes first.
