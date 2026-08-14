"""Create a reproducible business-state failure for the feedback loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from react_agent.apps.github_delivery import (
    DeliveryTask,
    GitHubDeliveryWorkflow,
    Replacement,
    WorkflowConfig,
)


def main() -> int:
    """Inject a contract mismatch and succeed only when tests contain it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()

    task = DeliveryTask(
        task_id="fault-issue-3-contract-mismatch",
        repository=str(args.repository.resolve()),
        issue_url=(
            "https://github.com/weihuaguo270-ops/agent-delivery-sandbox/issues/3"
        ),
        split="dev",
        replacements=(
            Replacement(
                "sandbox_service/policies.py",
                '    "task_03": 103,',
                '    "task_03": 999,',
            ),
        ),
        test_command=("python", "-m", "pytest", "-q"),
        acceptance_criteria=(
            "contract mismatch must be detected",
            "no external write occurs after failed tests",
        ),
    )
    report = GitHubDeliveryWorkflow(WorkflowConfig(
        artifact_dir=args.artifact_dir,
        mode="shadow",
    )).run(task, idempotency_key="fault:task_03:contract_mismatch:v1")
    (args.artifact_dir / "episode.json").write_text(
        json.dumps(report["episode"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.artifact_dir / "trajectory.json").write_text(
        json.dumps(report["episode"]["trajectory"], ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "passed": report["passed"],
        "alerts": report["alerts"],
        "external_write_count": report["metrics"]["external_write_count"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "test_failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
