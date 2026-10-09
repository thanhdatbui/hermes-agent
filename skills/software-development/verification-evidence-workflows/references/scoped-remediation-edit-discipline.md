# Scoped remediation edit discipline

For narrow fixes that edit tests with repeated mock/setup lines:

1. Use a unique anchor: test name plus nearby assertions. Avoid unqualified global replacements.
2. Re-read the affected diff immediately after each edit; a syntactically valid replacement can still target the wrong fixture or malformed mock seam.
3. Treat the exact user-specified test, compile, and diff-check commands as the closeout gate.
4. After any final test edit, discard earlier output and rerun every mandated command.
5. If an interruption or tool-call budget prevents verification, report it as incomplete; never imply the artifact is verified.

This reference captures the failure mode where repeated `urlopen` mock lines caused an ambiguous patch and verification ended before the requested commands ran.