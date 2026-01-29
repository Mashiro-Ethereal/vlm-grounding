from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional

from .validation import ValidationIssue, validate_dataset_dir, validate_trajectory_dir


def _print_issues(issues: Iterable[ValidationIssue]) -> None:
    for issue in issues:
        print(f"{issue.severity}: {issue.path}: {issue.message}")


def _exit_code(issues: List[ValidationIssue]) -> int:
    return 1 if any(issue.severity == "error" for issue in issues) else 0


def _validate_trajectory(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: path does not exist: {path}")
        return 2
    issues = validate_trajectory_dir(
        path,
        require_final_screenshot=args.require_final_screenshot,
        require_result=args.require_result,
    )
    if issues:
        _print_issues(issues)
    else:
        print("ok")
    return _exit_code(issues)


def _validate_dataset(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"error: path does not exist: {path}")
        return 2
    issues = validate_dataset_dir(path)
    if issues:
        _print_issues(issues)
    else:
        print("ok")
    return _exit_code(issues)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="data_format")
    subparsers = parser.add_subparsers(dest="command", required=True)

    trajectory_parser = subparsers.add_parser(
        "validate-trajectory",
        help="Validate a single trajectory directory.",
    )
    trajectory_parser.add_argument("path", help="Path to trajectory directory.")
    trajectory_parser.add_argument(
        "--require-final-screenshot",
        action="store_true",
        help="Treat missing final_screenshot.png as error.",
    )
    trajectory_parser.add_argument(
        "--require-result",
        action="store_true",
        help="Treat missing result.json as error.",
    )
    trajectory_parser.set_defaults(func=_validate_trajectory)

    dataset_parser = subparsers.add_parser(
        "validate-dataset",
        help="Validate a dataset directory containing trajectories/.",
    )
    dataset_parser.add_argument("path", help="Path to dataset directory.")
    dataset_parser.set_defaults(func=_validate_dataset)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
