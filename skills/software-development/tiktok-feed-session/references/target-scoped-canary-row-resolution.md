# Target-scoped canary row-resolution checklist

Use this checklist before any live `run-feed-session.ps1 ... -Run` canary.

## Identity evidence

Record from the exact authoritative workbook and canonical loader:

- logical `-Row` (1-based account slot)
- physical workbook/source row
- exact machine number
- exact ADB serial
- expected account/username

A machine-to-serial mapping is not enough when one machine has multiple account rows sharing that serial.

## Assignment evidence

Reconcile the selected row/account with:

- assignment manifest resources
- cohort artifact, if applicable
- worker identity
- scheduler/preflight state
- preserved busy/lock markers

A manifest containing only `machine:N` does not resolve the account row. A historical username, prior session, or plausible slot is not a binding.

## Fail-closed conditions

Stop before `-Run` if:

- more than one valid row remains and no authoritative row/account binding exists;
- the workbook or loader cannot resolve the row, serial, or account;
- a preflight blocker is present and the official runner cannot safely proceed.

Do not substitute manual ADB taps/input, cleanup, logout, fleet execution, or a guessed row.

## Required final report after an actual run

- exact command
- logical row and physical source row
- machine and serial
- account
- runner exit code
- `final_status`
- preserved run/artifact root
- fresh final screenshot path
- matching fresh `ui.xml` path
- account-switcher recovery pass/fail, based on the runner's fresh artifacts/logs rather than exit code alone
