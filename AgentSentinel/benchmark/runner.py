"""Run manually selected cases and save one result file per case."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.core import ToolUsingAgent
from benchmark.evaluator import evaluate_trace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = PROJECT_ROOT / "attacks" / "cases.json"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results"
REQUIRED_FIELDS = {
    "id",
    "task",
    "attack_type",
    "expected_behavior",
    "forbidden_behavior",
}
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    """Load and minimally validate experiment cases from JSON."""
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("cases.json must contain a JSON array")

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"case at index {index} must be an object")
        missing = REQUIRED_FIELDS - case.keys()
        if missing:
            raise ValueError(f"case at index {index} missing fields: {sorted(missing)}")
        for field in ("id", "task", "attack_type", "expected_behavior"):
            if not isinstance(case[field], str) or not case[field].strip():
                raise ValueError(f"case {index} field {field} must be a non-empty string")
        if not SAFE_NAME.fullmatch(case["id"]):
            raise ValueError(f"case id contains unsafe filename characters: {case['id']}")
        if case["id"] in seen_ids:
            raise ValueError(f"duplicate case id: {case['id']}")
        seen_ids.add(case["id"])
        _validate_forbidden_behavior(case["id"], case["forbidden_behavior"])
    return cases


def _validate_forbidden_behavior(case_id: str, rules: Any) -> None:
    if not isinstance(rules, list):
        raise ValueError(f"case {case_id} forbidden_behavior must be a list")
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("tool"), str):
            raise ValueError(f"case {case_id} forbidden rules require a tool name")
        if "arguments" in rule and not isinstance(rule["arguments"], dict):
            raise ValueError(f"case {case_id} forbidden rule arguments must be an object")


def select_cases(cases: list[dict[str, Any]], case_ids: list[str]) -> list[dict[str, Any]]:
    """Select cases in the same order as the requested IDs."""
    by_id = {case["id"]: case for case in cases}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise ValueError(f"unknown case ids: {missing}")
    return [by_id[case_id] for case_id in case_ids]


def save_result(
    case: dict[str, Any],
    model: str,
    trace: list[dict[str, Any]],
    task_success: bool,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
    run_id: str | None = None,
    defense_enabled: bool = False,
) -> Path:
    """Save a result with exclusive creation so old results are never overwritten."""
    run_id = run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"-{uuid.uuid4().hex[:8]}"
    )
    if not SAFE_NAME.fullmatch(run_id):
        raise ValueError("run_id contains unsafe filename characters")

    evaluation = evaluate_trace(trace, case["forbidden_behavior"])
    record = {
        "case_id": case["id"],
        "model": model,
        "trace": trace,
        "task_success": task_success,
        "attack_success": evaluation["attack_success"],
        "defense_enabled": defense_enabled,
        "matched_forbidden_behavior": evaluation["matches"],
    }
    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{case['id']}_{run_id}.json"
    with output_path.open("x", encoding="utf-8") as result_file:
        json.dump(record, result_file, ensure_ascii=False, indent=2)
    return output_path


def ask_task_success() -> bool:
    while True:
        answer = input("Did the agent complete the intended task? [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run manually selected AgentSentinel cases")
    parser.add_argument("--case", dest="case_ids", action="append", required=True)
    parser.add_argument("--cases-file", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--defense", choices=("off", "on"), default="off")
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="confirm that selected cases may call the configured API",
    )
    args = parser.parse_args()
    if not args.confirm_live:
        parser.error("--confirm-live is required; no experiment was run")

    cases = select_cases(load_cases(args.cases_file), args.case_ids)
    defense_enabled = args.defense == "on"
    agent = ToolUsingAgent(max_steps=args.max_steps, defense_enabled=defense_enabled)
    for case in cases:
        print(f"\nCase: {case['id']} ({case['attack_type']})")
        print(f"Task: {case['task']}")
        result = agent.run(case["task"])
        print(f"Agent output: {result.output}")
        print("Trace:", json.dumps(result.trace, ensure_ascii=False, indent=2))
        output_path = save_result(
            case,
            agent.model,
            result.trace,
            ask_task_success(),
            args.results_dir,
            defense_enabled=defense_enabled,
        )
        print(f"Saved result: {output_path}")


if __name__ == "__main__":
    main()
