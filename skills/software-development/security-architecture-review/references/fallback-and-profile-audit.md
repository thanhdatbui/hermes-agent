# Fallback and Profile Audit Reference

## Evidence matrix

| Question | Inspect | Do not infer from |
|---|---|---|
| Host or profile route? | subprocess command, `env=`, effective HOME/USERPROFILE | log label or profile name |
| Which account is active? | non-secret identity claim from the credential actually read | `old` account lists or UI labels |
| Which network route? | effective proxy variables, `NO_PROXY`, client behavior, fallback branch | proxy field in config alone |
| Is the fallback locked? | lock acquisition/release around the fallback call | pool status output |
| Is isolation complete? | registry/absolute paths/inherited env/privilege analysis | unique UUIDs or directories |

## Report template

1. **VERDICT:** VERIFIED / PENDING / BLOCKED / UNKNOWN
2. **Coordinator probe:** exact file/line or runtime artifact; redact secrets.
3. **Reviewer finding:** quote or summarize only what the reviewer actually completed.
4. **Confirmed risk:** state impact and trigger.
5. **Pending proof:** name the missing runtime test or artifact.
6. **Next action:** smallest defensive fix or verification step.

## Common corrections

- `subprocess.run(cmd)` without `env=` is host-default execution, not a profile route.
- A credential file's active token identity outranks an account-history list for determining which account the CLI will use.
- Environment-variable sandboxing is soft isolation; it is not a Windows security boundary.
- A proxy configured in a profile is not proof that every binary honors the proxy.
- Do not expose proxy credentials, access tokens, refresh tokens, or passwords in reports.
- Do not call a static uniqueness check “100% secure” or “fake chuẩn”.
