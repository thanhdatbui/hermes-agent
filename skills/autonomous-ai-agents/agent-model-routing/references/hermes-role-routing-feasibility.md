# Hermes role-routing feasibility

This note separates a desired multi-model architecture from what stock Hermes can express directly.

## Native primitives

### Main session

- One active main model/provider per session.
- `/model` is session-scoped; a global default affects new sessions.

### `delegate_task`

- One global delegation pin: `delegation.provider`, `delegation.model`, and `delegation.reasoning_effort`.
- The tool schema has **no per-call model field**. Every child in a batch uses the same configured delegation model, or inherits the parent when the pin is empty.
- Therefore stock `delegate_task` cannot express "Flash routine worker, Pro quality worker, Luna quota worker" dynamically within one parent session.

### Main fallback chain

- `fallback_providers` is a real YAML list of `{provider, model, ...}` entries, managed safely with `hermes fallback add/remove/list`.
- It activates for transport/rate-limit/overload/connection failures. It is not semantic routing based on task difficulty or an auditor verdict.
- Do not use `hermes config set fallback_providers '<JSON>'` unless parsing is verified: it may store a quoted string. `hermes fallback list` is the acceptance test; if it says no chain, no fallback is active.

### Auxiliary models and task-specific fallback

- Compression model lives at `auxiliary.compression.{provider,model}`, not `compression.model`. Keys mistakenly placed under the top-level `compression:` block do not select the summarizer; that block controls compression lifecycle/threshold policy.
- A task-specific fallback is a YAML list at `auxiliary.compression.fallback_chain`; it is independent of the main session's top-level fallback chain.
- Example shape:

  ```yaml
  auxiliary:
    compression:
      provider: custom:router
      model: fast-model
      fallback_chain:
        - provider: router
          model: backup-model
  ```

- Hermes skips a fallback entry whose normalized provider label equals the provider that just failed. When primary and fallback use the same local endpoint but different upstream models, verify whether distinct named-provider labels both resolve to that endpoint; do not assume two spellings are equivalent without resolver evidence.
- Acceptance checks: parse raw YAML; inspect `load_config().auxiliary.compression`; resolve the primary with `_resolve_task_provider_model("compression")`; resolve the candidate with `_try_configured_fallback_chain(...)`; run `hermes config check`; then confirm a later compression request/log uses the expected route. A compression that already happened cannot be retroactively rebilled.
- Vision and other auxiliary tasks have their own `auxiliary.<task>` routes.

### Profiles / Kanban / external CLIs

Use these when one global worker pin is insufficient:

- **Profiles**: separate configs per role (planner, Flash worker, Luna overflow worker, auditor). Profiles can carry descriptions and be assigned to Kanban tasks.
- **Kanban dispatcher**: durable role/profile routing; suitable for explicit task types and workflows.
- **External CLI one-shots**: Claude CLI or other coding CLIs for expert review. These are subprocesses, not native `delegate_task` children.
- **Custom dispatcher/plugin**: required for automatic semantic routing (difficulty classification, quota-aware model choice, audit escalation) inside one conversational workflow.

## Recommended separation of triggers

Do not collapse these into one fallback list:

1. **Quality escalation**: worker output fails tests/acceptance → stronger worker/reviewer while the original provider still has quota.
2. **Quota/transport fallback**: provider pool is exhausted/unavailable → different healthy account/pool/provider.
3. **Audit escalation**: risk class or reviewer disagreement → independent reviewer model/family.

A stronger model in the same exhausted shared account is not a quota fallback.

## Implementation checklist

1. Verify live model IDs and account pools.
2. Choose the main coordinator model per session/profile.
3. Pin one routine child model under `delegation.*`.
4. Add only cross-provider quota/transport fallbacks with `hermes fallback add`; verify using `hermes fallback list`.
5. Configure compression under `auxiliary.compression.*` and verify the next auxiliary log line.
6. Implement stronger-worker and audit lanes as profiles/Kanban/external CLI steps, not as imagined native per-call delegation.
7. Test each lane with a harmless task and capture provider/model evidence.

## Multi-account safety

Credential pools can rotate supported credentials, but buying accounts or assigning proxies to evade provider restrictions is not a reliability guarantee and may violate terms. More accounts can reduce load per account only when the provider supports that pool; it does not erase client fingerprint, IP/ASN, behavior, payment, or linked-account signals. Never quote a ban-risk percentage without measured provider-specific evidence.