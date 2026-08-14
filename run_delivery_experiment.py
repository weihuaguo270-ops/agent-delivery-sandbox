"""Run the frozen GitHub delivery dataset through react-agent v0.9+."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from react_agent.apps.github_delivery import (
    Approval,
    DeliveryTask,
    GitHubDeliveryWorkflow,
    Replacement,
    WorkflowConfig,
)


def _task(case: dict, repository: Path) -> DeliveryTask:
    case_id = case["case_id"]
    old = case["old"]
    new = case["new"]
    return DeliveryTask(
        task_id=f"issue-{case['issue']}-{case_id}",
        repository=str(repository.resolve()),
        issue_url=(
            "https://github.com/weihuaguo270-ops/agent-delivery-sandbox/"
            f"issues/{case['issue']}"
        ),
        split=case["split"],
        replacements=(
            Replacement(
                "sandbox_service/policies.py",
                f'    "{case_id}": {old},',
                f'    "{case_id}": {new},',
            ),
            Replacement(
                "sandbox_service/contracts.py",
                f'    "{case_id}": {old},',
                f'    "{case_id}": {new},',
            ),
        ),
        test_command=("python", "-m", "pytest", "-q"),
        acceptance_criteria=(
            "all repository tests pass",
            f"only {case_id} policy and contract change",
            "source issue is preserved",
        ),
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile))
    return round(ordered[index], 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("dataset/manifest.json"))
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("shadow", "guarded"), default="shadow")
    parser.add_argument("--approval-dir", type=Path)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--publish-draft-pr", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    selected = [
        case for case in manifest["cases"]
        if not args.case_ids or case["case_id"] in args.case_ids
    ]
    workflow = GitHubDeliveryWorkflow(WorkflowConfig(
        artifact_dir=args.artifact_dir,
        mode=args.mode,
        publish_draft_pr=args.publish_draft_pr,
    ))
    reports = []
    episode_dir = args.artifact_dir / "episodes"
    trajectory_dir = args.artifact_dir / "trajectories"
    episode_dir.mkdir(parents=True, exist_ok=True)
    trajectory_dir.mkdir(parents=True, exist_ok=True)
    for case in selected:
        approval = None
        if args.approval_dir:
            approval_path = args.approval_dir / f"{case['case_id']}.json"
            if approval_path.exists():
                approval = Approval.from_dict(json.loads(approval_path.read_text(encoding="utf-8")))
        report = workflow.run(
            _task(case, args.repository),
            approval=approval,
            idempotency_key=f"{args.mode}:{case['case_id']}:v1",
        )
        reports.append(report)
        (episode_dir / f"{case['case_id']}.json").write_text(
            json.dumps(report["episode"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (trajectory_dir / f"{case['case_id']}.json").write_text(
            json.dumps(
                report["episode"]["trajectory"], ensure_ascii=False, indent=2
            ) + "\n",
            encoding="utf-8",
        )

    durations = [float(report["metrics"]["workflow_duration_ms"]) for report in reports]
    summary = {
        "schema_version": "agent-delivery-experiment/v1",
        "mode": args.mode,
        "cases": len(reports),
        "passed": sum(report["passed"] for report in reports),
        "task_success_rate": (
            sum(report["passed"] for report in reports) / len(reports) if reports else 0.0
        ),
        "human_takeover_rate": (
            sum(report["metrics"]["human_takeover_required"] for report in reports)
            / len(reports) if reports else 0.0
        ),
        "external_write_count": sum(
            report["metrics"]["external_write_count"] for report in reports
        ),
        "latency_ms": {
            "mean": round(statistics.fmean(durations), 3) if durations else 0.0,
            "p95": _percentile(durations, 0.95),
        },
        "statuses": {
            status: sum(report["status"] == status for report in reports)
            for status in sorted({report["status"] for report in reports})
        },
        "report_run_ids": [report["run_id"] for report in reports],
    }
    (args.artifact_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] == len(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
