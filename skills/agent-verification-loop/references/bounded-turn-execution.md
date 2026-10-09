# Bounded-turn execution discipline

Use this reference when a task specifies a hard iteration/tool-turn cap or exactly one focused test.

1. Treat the cap as part of the acceptance contract. Batch repository binding, dirty-path snapshot, and named-anchor reads in the first inspection turn.
2. Reserve the final turn for the smallest authorized write (if evidence proves a fix), the single mandated verifier, and scoped status/diff evidence.
3. Do not spend the budget on exploratory pytest runs, live/device probes, full-suite runs, or redundant re-reads.
4. If the verifier was not executed, report `NOT RUN` explicitly. Never convert a planned command or a tool failure into a passing result.
5. If evidence proves the defect is outside the allowlist, stop with `ABORT/NO PATCH`, exact artifact anchor, and proposed contract rather than forcing a caller-side edit.
