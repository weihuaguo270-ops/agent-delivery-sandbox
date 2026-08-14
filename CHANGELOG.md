# Changelog

## 0.1.1 (2026-08-14)

### Evidence

- Final human review completed for PR #28
- Selected release set `task_01 + task_18` passed business state, performance,
  dataset audit, human review, and trajectory failure gates
- Rejected `task_02` and rolled-back `task_17` remain excluded with their evidence preserved

## 0.1.0 (2026-08-14)

### Added

- Frozen 24-Issue dev/golden/held-out delivery dataset
- Shadow and guarded execution through react-agent v0.9.0
- Real Draft PR acceptance, rejection, cleanup, pending-review, and rollback cases
- Bearer-protected evidence and approval control plane with request IDs and JSON logs
- Reproducible contract-mismatch fault injection
- Cross-project failure feedback through trace-debugger v0.5.0 and llm-eval-engine v0.5.0

### Evidence

- Shadow 24/24, P95 606.258 ms
- Guarded Draft PR creation 4/4, P95 8457.034 ms
- Finalized candidate acceptance 2/3; one open Draft remains pending
- Rollback 1/1 through PR #29
- Comprehensive release decision remains `hold` because rejection and pending review are preserved
