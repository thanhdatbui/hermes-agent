# Target-scoped canary row-resolution checklist

Use this checklist before any live workbook-backed device canary.

## Identity evidence

Record from the exact authoritative workbook and canonical loader:

- logical `-Row` (1-based account slot)
- physical workbook/source row
- exact machine number
- exact ADB serial
- expected account/username

A machine-to-serial mapping is not enough when one machine has multiple account rows sharing that serial.

## Assignment evidence

Reconcile the selected row/account with assignment manifest resources, cohort artifact, worker identity, and scheduler/preflight state. A manifest containing only `machine:N` does not resolve the account row. A historical username, prior session, or plausible slot is not a binding.

## Fail-closed conditions

Stop before `-Run` if more than one valid row remains without an authoritative row/account binding, if the workbook/loader cannot resolve the row/serial/account, or if a concrete preflight blocker remains. Do not substitute manual ADB taps/input, cleanup, logout, fleet execution, or a guessed row.

## Required report after an actual run

Report the exact command, logical row and physical source row, machine and serial, account, runner exit code, `final_status`, preserved run/artifact root, fresh final screenshot, matching `ui.xml`, and account-switcher recovery result based on fresh artifacts/logs rather than exit code alone.
