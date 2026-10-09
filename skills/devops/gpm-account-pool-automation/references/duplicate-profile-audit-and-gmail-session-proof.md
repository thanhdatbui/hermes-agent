# Duplicate GPM profile audit and Gmail-session proof

## Scope and safety
Use this for a read-only audit. Do not start either profile, attach to CDP, or interact with browser UI. Query only non-mutating inventory/list endpoints and inspect local metadata/logs.

## Evidence matrix
- Same display name/email: identity/configuration clue only.
- Same proxy, port, group, timezone, or browser version: configuration clue only.
- Different profile IDs or `ProfilePath` values: separate stored profile records; not proof of different Gmail state.
- `CreatedAt`, `LastRunAt`, `UpdatedAt`: chronology only; `LastRunAt` does not prove successful Gmail authentication.
- `JsonData` containing the email in `Name`: usually just copied profile naming metadata. It does not prove cookies, tokens, or a Gmail session.
- Historical logs: useful for chronology/errors when they contain target IDs, but absence of an ID/email is not proof of absence.
- Gmail session proof requires direct, read-only evidence from persisted browser state or an existing explicit session artifact that records authenticated Gmail state. Do not launch the profile to obtain it.

## Procedure
1. Locate the GPM metadata SQLite database and inspect the `Profiles` schema.
2. Compare target rows by `Id`, `Name`, `ProfilePath`, `GroupId`, timestamps, and parsed non-secret `JsonData`.
3. Query the local inventory/list API without mutating state; compare its result with SQLite and report API/database divergence.
4. Search only targeted logs/artifacts for the target IDs and email. Bound broad repository searches to avoid hangs.
5. Redact proxy credentials, cookies, refresh tokens, and other secrets from notes and final output.
6. State the conclusion with an evidence boundary: metadata can establish duplicate records and configuration similarity, but cannot establish which profile has an authenticated Gmail session.

## Reusable report format
- Records found and distinguishing fields.
- Duplicate assessment: same name/config vs distinct IDs/paths.
- API vs database consistency.
- Session-proof status for each profile: proven / not proven / indeterminate, with exact evidence.
- Actions not taken: no profile start, no browser/CDP interaction, no writes.
